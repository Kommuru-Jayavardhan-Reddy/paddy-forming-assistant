"""
Paddy Farming Assistant - Live Market Price Service (STEP 11G.1)
Fetches and structures official agricultural mandi commodity spot prices
from the National Open Government Data (OGD) Platform India (data.gov.in / Agmarknet).
Preserves strict scientific data integrity without fabricating synthetic prices.
"""

import sys
import logging
from decimal import Decimal, InvalidOperation
from datetime import date, datetime, timezone
from typing import Dict, Any, List, Optional, Tuple

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app import config
from app.exceptions import (
    MarketServiceDisabledError,
    MarketApiKeyMissingError,
    MarketProviderError,
    MarketServiceUnavailableError,
    MarketParsingError,
)
from app.db.models.market import MarketPrice

logger = logging.getLogger(__name__)


def parse_arrival_date(raw_date: str) -> date:
    """Parses arrival date string in DD/MM/YYYY or YYYY-MM-DD format."""
    cleaned = raw_date.strip()
    if "/" in cleaned:
        parts = cleaned.split("/")
        if len(parts) == 3:
            # DD/MM/YYYY
            day, month, year = int(parts[0]), int(parts[1]), int(parts[2])
            return date(year, month, day)
    return date.fromisoformat(cleaned)


class MarketService:
    """
    Client for live agricultural market mandi prices from the official
    Data.gov.in OGD API / Agmarknet federated dataset.
    """

    _instance: Optional["MarketService"] = None

    def __init__(self):
        self._session = requests.Session()
        retries = Retry(
            total=2,
            backoff_factor=0.5,
            status_forcelist=[500, 502, 503, 504],
            raise_on_status=False,
        )
        adapter = HTTPAdapter(max_retries=retries)
        self._session.mount("https://", adapter)
        self._session.mount("http://", adapter)
        self._session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 (PaddyFarmingAssistant/1.0)",
            "Accept": "application/json",
        })
        self._sync_cooldowns: Dict[Tuple[str, Optional[str]], datetime] = {}

    def is_in_cooldown(self, state: str, district: Optional[str]) -> bool:
        """Determines if a live sync request for the given state/district was performed recently."""
        key = (state.strip().lower(), district.strip().lower() if district else None)
        last_time = self._sync_cooldowns.get(key)
        if not last_time:
            return False
        elapsed = (datetime.now(timezone.utc) - last_time).total_seconds()
        return elapsed < (config.MARKET_SYNC_COOLDOWN_MINUTES * 60)

    def record_sync_attempt(self, state: str, district: Optional[str]):
        """Records timestamp of an attempted sync to prevent rapid repeated upstream requests."""
        key = (state.strip().lower(), district.strip().lower() if district else None)
        self._sync_cooldowns[key] = datetime.now(timezone.utc)

    def clear_cooldowns(self):
        """Clears all in-memory sync cooldowns."""
        self._sync_cooldowns.clear()

    @classmethod
    def get_instance(cls) -> "MarketService":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def probe_upstream_availability(self) -> Dict[str, Any]:
        """
        Probes the upstream Data.gov.in endpoint to determine connectivity,
        API responsiveness, and authentication requirement status without exposing credentials.
        """
        api_key = config.DATAGOVIN_API_KEY
        masked_key = f"{api_key[:4]}...{api_key[-4:]}" if api_key and len(api_key) > 8 else ("Configured" if api_key else "Not Configured")

        result = {
            "provider": config.MARKET_PROVIDER,
            "resource_id": config.DATAGOVIN_RESOURCE_ID,
            "endpoint_url": config.DATAGOVIN_BASE_URL,
            "api_key_configured": bool(api_key),
            "api_key_status": masked_key,
            "service_enabled": config.MARKET_SERVICE_ENABLED,
            "upstream_reachable": False,
            "status_code": None,
            "detail": None,
        }

        try:
            params = {"format": "json", "limit": 1}
            if api_key:
                params["api-key"] = api_key

            response = self._session.get(
                config.DATAGOVIN_BASE_URL,
                params=params,
                timeout=config.MARKET_REQUEST_TIMEOUT_SECONDS,
            )
            result["status_code"] = response.status_code
            result["upstream_reachable"] = True

            if response.status_code == 200:
                result["detail"] = "Upstream API active and authorized."
            elif response.status_code == 400:
                result["detail"] = "Upstream active. Key missing: 'Authorization field missing'."
            elif response.status_code == 403:
                result["detail"] = "Upstream active. Key rejected: 'Key not authorised'."
            else:
                result["detail"] = f"Upstream returned HTTP {response.status_code}."

        except requests.exceptions.Timeout:
            result["detail"] = f"Connection to {config.DATAGOVIN_BASE_URL} timed out ({config.MARKET_REQUEST_TIMEOUT_SECONDS}s)."
        except requests.exceptions.RequestException as exc:
            result["detail"] = f"Network connection error: {exc.__class__.__name__}."

        return result

    def fetch_live_paddy_prices_detailed(
        self,
        district: Optional[str] = None,
        state: str = "Andhra Pradesh",
        limit: int = 50,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """
        Fetches live mandi commodity prices for Paddy from the official Data.gov.in API
        with complete diagnostic metadata (raw count, accepted count, rejected count).
        Never fabricates placeholder prices if credentials or service is unavailable.
        """
        if not config.MARKET_SERVICE_ENABLED:
            raise MarketServiceDisabledError("Market price service is disabled in configuration.")

        if not config.DATAGOVIN_API_KEY:
            raise MarketApiKeyMissingError(
                "Data.gov.in API key is not configured. Please set DATAGOVIN_API_KEY in the backend environment."
            )

        safe_limit = min(max(1, limit), 200)
        safe_offset = max(0, offset)

        params: Dict[str, Any] = {
            "api-key": config.DATAGOVIN_API_KEY,
            "format": "json",
            "offset": safe_offset,
            "limit": safe_limit,
            "filters[state]": state,
            "filters[commodity]": "Paddy(Dhan)",
        }
        if district:
            params["filters[district]"] = district.strip()

        try:
            response = self._session.get(
                config.DATAGOVIN_BASE_URL,
                params=params,
                timeout=config.MARKET_REQUEST_TIMEOUT_SECONDS,
            )
        except requests.exceptions.Timeout as exc:
            logger.error("Data.gov.in API timed out after %s seconds.", config.MARKET_REQUEST_TIMEOUT_SECONDS)
            raise MarketServiceUnavailableError("Market price provider timed out.") from exc
        except requests.exceptions.RequestException as exc:
            logger.error("Data.gov.in network failure: %s", exc)
            raise MarketServiceUnavailableError(f"Could not connect to market price provider: {exc.__class__.__name__}") from exc

        if response.status_code == 400:
            err_msg = response.json().get("error", "Bad Request") if response.text else "Bad Request"
            raise MarketApiKeyMissingError(f"Data.gov.in rejected request: {err_msg}")
        elif response.status_code == 403:
            err_msg = response.json().get("error", "Forbidden") if response.text else "Forbidden"
            raise MarketProviderError(f"Data.gov.in API authorization failed: {err_msg}. Verify DATAGOVIN_API_KEY.")
        elif response.status_code >= 500:
            raise MarketServiceUnavailableError(f"Data.gov.in provider returned HTTP {response.status_code}.")
        elif response.status_code != 200:
            raise MarketProviderError(f"Data.gov.in returned unexpected HTTP status {response.status_code}.")

        try:
            payload = response.json()
        except Exception as exc:
            raise MarketParsingError("Data.gov.in response is not valid JSON.") from exc

        raw_records = payload.get("records", [])
        total_count = int(payload.get("total", len(raw_records)))

        valid_prices: List[Dict[str, Any]] = []
        rejected_count = 0
        for r in raw_records:
            try:
                min_p = Decimal(str(r["min_price"]).strip())
                max_p = Decimal(str(r["max_price"]).strip())
                modal_p = Decimal(str(r["modal_price"]).strip())
                arr_date = parse_arrival_date(str(r.get("arrival_date", "")).strip())

                if min_p >= 0 and max_p >= min_p and modal_p >= min_p and modal_p <= max_p:
                    valid_prices.append({
                        "market_name": str(r.get("market") or r.get("market_name") or "Unknown Mandi").strip()[:150],
                        "district": str(r.get("district", district or "Unknown")).strip()[:100],
                        "state": str(r.get("state", state)).strip()[:100],
                        "commodity": str(r.get("commodity", "Paddy (Dhan)")).strip()[:100],
                        "variety": str(r.get("variety", "Common")).strip()[:100],
                        "grade": str(r.get("grade", "FAQ")).strip()[:50],
                        "min_price": min_p,
                        "max_price": max_p,
                        "modal_price": modal_p,
                        "currency": "INR",
                        "unit": "Quintal",
                        "price_date": arr_date,
                        "source": "Agmarknet via Data.gov.in",
                    })
                else:
                    rejected_count += 1
            except (KeyError, ValueError, InvalidOperation) as parse_err:
                logger.warning("Skipping unparseable market record: %s (Error: %s)", r, parse_err)
                rejected_count += 1

        return {
            "valid_prices": valid_prices,
            "raw_retrieved": len(raw_records),
            "records_accepted": len(valid_prices),
            "records_rejected": rejected_count,
            "total_upstream": total_count,
            "upstream_status_code": response.status_code,
        }

    def fetch_live_paddy_prices(
        self,
        district: Optional[str] = None,
        state: str = "Andhra Pradesh",
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Fetches live mandi commodity prices for Paddy from the official Data.gov.in API.
        Returns (valid_prices, total_count) for backward compatibility.
        """
        res = self.fetch_live_paddy_prices_detailed(
            district=district,
            state=state,
            limit=limit,
            offset=offset,
        )
        return res["valid_prices"], res["total_upstream"]

    async def cache_market_prices(
        self,
        session: AsyncSession,
        prices: List[Dict[str, Any]],
    ) -> int:
        """
        Persists authentic fetched market prices into the PostgreSQL 'market_prices' table idempotently
        via MarketPriceRepository.
        """
        if not prices:
            return 0

        from app.db.repositories.other_repositories import MarketPriceRepository
        repo = MarketPriceRepository(session)
        cached_count = await repo.upsert_prices(prices)
        await session.commit()
        logger.info("Cached %d market price quotations into database.", cached_count)
        return cached_count

    async def get_prices_with_fallback(
        self,
        session: AsyncSession,
        state: Optional[str] = None,
        district: Optional[str] = None,
        commodity: Optional[str] = None,
        variety: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
        force_live: bool = False,
    ) -> Dict[str, Any]:
        """
        Retrieves market prices utilizing a safe, intelligent live/local fallback strategy.
        1. Queries local PostgreSQL database via MarketPriceRepository.
        2. If local records exist and are fresh (<= MARKET_STALENESS_DAYS) and not force_live:
           Returns local database records immediately (data_source='database_cache').
        3. If local records are missing or stale (or force_live=True):
           Attempts Data.gov.in retrieval ONLY IF service enabled and DATAGOVIN_API_KEY is configured.
           On successful upstream response: validates records, caches atomically in PostgreSQL,
           and returns fresh records (data_source='live_synced').
        4. If live retrieval is blocked, times out, or fails:
           Falls back to available local records (data_source='database_stale', is_stale=True).
           If no local records exist, returns valid empty response (data_source='empty').
        Never fabricates placeholder prices.
        """
        from app.db.repositories.other_repositories import MarketPriceRepository
        from fastapi.concurrency import run_in_threadpool

        target_state = state or "Andhra Pradesh"
        repo = MarketPriceRepository(session)

        # Step 1: Query existing local records
        local_records, local_total = await repo.list_latest_prices(
            district=district,
            commodity=commodity,
            variety=variety,
            state=state,
            skip=skip,
            limit=limit,
        )

        today = datetime.now(timezone.utc).date()
        latest_date = local_records[0].price_date if local_records else None

        is_stale = False
        if latest_date:
            age_days = (today - latest_date).days
            if age_days > config.MARKET_STALENESS_DAYS:
                is_stale = True
        else:
            is_stale = True

        # If records exist, are fresh, and user did not force live sync -> return database cache
        if local_records and not is_stale and not force_live:
            return {
                "items": local_records,
                "total": local_total,
                "skip": skip,
                "limit": limit,
                "data_source": "database_cache",
                "is_stale": False,
                "freshness_date": latest_date,
            }

        # Step 2: Attempt live retrieval if configured and not cooled down
        can_attempt_live = (
            config.MARKET_SERVICE_ENABLED
            and bool(config.DATAGOVIN_API_KEY)
            and (force_live or not self.is_in_cooldown(target_state, district))
        )

        if can_attempt_live:
            try:
                detailed = await run_in_threadpool(
                    self.fetch_live_paddy_prices_detailed,
                    district=district,
                    state=target_state,
                    limit=max(limit, 50),
                    offset=0,
                )
                self.record_sync_attempt(target_state, district)

                if detailed["valid_prices"]:
                    try:
                        await repo.upsert_prices(detailed["valid_prices"])
                        await session.commit()
                    except Exception as cache_err:
                        logger.warning(
                            "Database cache write failed during live sync (%s: %s). Transaction rolled back.",
                            cache_err.__class__.__name__,
                            cache_err,
                        )
                        await session.rollback()

                    # Query fresh records from database
                    fresh_records, fresh_total = await repo.list_latest_prices(
                        district=district,
                        commodity=commodity,
                        variety=variety,
                        state=state,
                        skip=skip,
                        limit=limit,
                    )
                    if fresh_records:
                        return {
                            "items": fresh_records,
                            "total": fresh_total,
                            "skip": skip,
                            "limit": limit,
                            "data_source": "live_synced",
                            "is_stale": False,
                            "freshness_date": fresh_records[0].price_date,
                        }
                else:
                    logger.info("Upstream returned 0 matching market records; falling back to local database.")

            except Exception as live_err:
                logger.warning(
                    "Live market retrieval failed (%s: %s). Falling back to local database.",
                    live_err.__class__.__name__,
                    live_err,
                )
                self.record_sync_attempt(target_state, district)

        # Step 3: Fallback to local records (or empty)
        if local_records:
            return {
                "items": local_records,
                "total": local_total,
                "skip": skip,
                "limit": limit,
                "data_source": "database_stale" if is_stale else "database_cache",
                "is_stale": is_stale,
                "freshness_date": latest_date,
            }

        return {
            "items": [],
            "total": 0,
            "skip": skip,
            "limit": limit,
            "data_source": "empty",
            "is_stale": False,
            "freshness_date": None,
        }


market_service = MarketService.get_instance()

