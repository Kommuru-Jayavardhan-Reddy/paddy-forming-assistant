"""
Paddy Farming Assistant - SMS OTP Delivery Service
Provides real SMS gateway integration (Twilio, Fast2SMS, MSG91, and Generic HTTP Gateway)
with strict separation between Production and Development/Testing modes.

Guarantees:
- Production Mode requires real, verified SMS credentials via environment variables.
- Missing credentials in Production fail securely without bypassing verification.
- Test/Dev OTPs are strictly prohibited in Production.
- In Development Mode, configurable mock/test dispatch enables automated testing.
- Single-use, time-limited OTP delivery with privacy masking in logs.
"""

import os
import re
import json
import logging
import asyncio
from typing import Optional, Dict, Any, Tuple
from dataclasses import dataclass
import requests

from app import config

logger = logging.getLogger(__name__)


class SMSDeliveryError(Exception):
    """Raised when SMS delivery fails or cannot proceed due to misconfiguration."""
    pass


class SMSConfigurationError(SMSDeliveryError):
    """Raised when production SMS provider credentials are missing."""
    pass


@dataclass
class SMSDispatchResult:
    """Represents the outcome of an SMS dispatch operation."""
    success: bool
    provider: str
    message_id: Optional[str] = None
    detail: Optional[str] = None
    dev_otp: Optional[str] = None


def mask_phone_number(phone: str) -> str:
    """Masks phone number for privacy-compliant logging and UI display (e.g. +91 938****129)."""
    if not phone:
        return "Unknown"
    digits = re.sub(r"[^\d+]", "", phone)
    if len(digits) >= 10:
        return f"{digits[:6]}****{digits[-3:]}"
    return f"{digits[:2]}****"


class SMSService:
    """
    Central SMS Dispatch Service supporting multiple real gateways
    and safe development simulation.
    """

    def __init__(self):
        self.reload_config()
        # In-memory test store for automated testing assertions
        self._sent_messages: list[Dict[str, Any]] = []

    def reload_config(self) -> None:
        """
        Dynamically refreshes environment variables so live updates in .env
        take effect immediately without needing server restart.
        """
        # Environment resolution
        self.env = os.getenv("SMS_ENVIRONMENT", config.ENVIRONMENT).lower()
        self.is_production = (self.env == "production")
        self.dev_otp_enabled = os.getenv("DEV_OTP_ENABLED", "True").lower() in ("true", "1", "yes") and not self.is_production

        # Provider selection ('auto', 'twilio', 'fast2sms', 'msg91', 'generic', 'mock')
        self.configured_provider = os.getenv("SMS_PROVIDER", "auto").lower()

        # Twilio credentials
        self.twilio_account_sid = os.getenv("TWILIO_ACCOUNT_SID", "").strip()
        self.twilio_auth_token = os.getenv("TWILIO_AUTH_TOKEN", "").strip()
        self.twilio_from_number = os.getenv("TWILIO_FROM_NUMBER", "").strip()
        self.twilio_messaging_service_sid = os.getenv("TWILIO_MESSAGING_SERVICE_SID", "").strip()

        # Fast2SMS credentials (official API https://docs.fast2sms.com/reference)
        self.fast2sms_api_key = os.getenv("FAST2SMS_API_KEY", "").strip()
        self.fast2sms_otp_id = os.getenv("FAST2SMS_OTP_ID", "").strip()
        self.fast2sms_route = os.getenv("FAST2SMS_ROUTE", "auto").lower().strip()
        self.fast2sms_sender_id = os.getenv("FAST2SMS_SENDER_ID", "").strip()
        self.fast2sms_message_id = os.getenv("FAST2SMS_MESSAGE_ID", "").strip()

        # MSG91 credentials (Indian SMS gateway)
        self.msg91_auth_key = os.getenv("MSG91_AUTH_KEY", "").strip()
        self.msg91_template_id = os.getenv("MSG91_TEMPLATE_ID", "").strip()

        # Generic HTTP Gateway credentials
        self.sms_gateway_url = os.getenv("SMS_GATEWAY_URL", "").strip()
        self.sms_gateway_api_key = os.getenv("SMS_GATEWAY_API_KEY", "").strip()
        self.sms_gateway_method = os.getenv("SMS_GATEWAY_METHOD", "POST").upper()

    def get_active_provider_name(self) -> str:
        """Determines the active provider based on configured credentials and environment."""
        self.reload_config()

        if self.configured_provider != "auto":
            return self.configured_provider

        if self.twilio_account_sid and self.twilio_auth_token and (self.twilio_from_number or self.twilio_messaging_service_sid):
            return "twilio"
        if self.fast2sms_api_key:
            return "fast2sms"
        if self.msg91_auth_key and self.msg91_template_id:
            return "msg91"
        if self.sms_gateway_url:
            return "generic"

        return "mock" if not self.is_production else "none"

    def is_real_provider_configured(self) -> bool:
        """Returns True if valid production SMS gateway credentials are present."""
        return self.get_active_provider_name() in ("twilio", "fast2sms", "msg91", "generic")

    async def send_otp(self, normalized_mobile: str, otp: str) -> SMSDispatchResult:
        """
        Dispatches a 6-digit OTP to the recipient's phone number.
        Enforces strict production safeguards.
        """
        masked = mask_phone_number(normalized_mobile)
        message_text = (
            f"Your Paddy Farming Assistant verification code is {otp}. "
            "Valid for 5 minutes. Do not share this OTP with anyone."
        )

        provider = self.get_active_provider_name()

        # Production Mode Validation
        if self.is_production:
            if provider in ("mock", "none"):
                logger.critical(
                    "Production SMS dispatch blocked: No real SMS provider credentials configured for %s",
                    masked
                )
                raise SMSConfigurationError(
                    "Production SMS service is unconfigured. Please configure SMS credentials in environment variables."
                )

        # Real Provider 1: Twilio
        if provider == "twilio":
            return await asyncio.to_thread(self._send_via_twilio, normalized_mobile, message_text)

        # Real Provider 2: Fast2SMS
        if provider == "fast2sms":
            return await asyncio.to_thread(self._send_via_fast2sms, normalized_mobile, otp)

        # Real Provider 3: MSG91
        if provider == "msg91":
            return await asyncio.to_thread(self._send_via_msg91, normalized_mobile, otp)

        # Real Provider 4: Generic HTTP Gateway
        if provider == "generic":
            return await asyncio.to_thread(self._send_via_generic, normalized_mobile, message_text, otp)

        # Development / Testing Simulation Mode
        logger.info(
            "[DEV MODE] SMS OTP simulated for %s (Provider: %s).",
            masked,
            provider
        )
        record = {
            "mobile": normalized_mobile,
            "otp": otp,
            "provider": "mock",
            "message": message_text,
        }
        self._sent_messages.append(record)

        dev_otp_value = otp if self.dev_otp_enabled else None
        return SMSDispatchResult(
            success=True,
            provider="mock",
            message_id=f"mock-{os.urandom(4).hex()}",
            detail="OTP delivered via Development Sandbox simulation.",
            dev_otp=dev_otp_value,
        )

    def _send_via_twilio(self, to_number: str, text: str) -> SMSDispatchResult:
        """Sends SMS via Twilio REST API without requiring external SDK."""
        url = f"https://api.twilio.com/2010-04-01/Accounts/{self.twilio_account_sid}/Messages.json"
        data = {
            "To": to_number,
            "Body": text,
        }
        if self.twilio_messaging_service_sid:
            data["MessagingServiceSid"] = self.twilio_messaging_service_sid
        else:
            data["From"] = self.twilio_from_number

        try:
            resp = requests.post(
                url,
                data=data,
                auth=(self.twilio_account_sid, self.twilio_auth_token),
                timeout=12,
            )
            if resp.status_code in (200, 201):
                res_json = resp.json()
                sid = res_json.get("sid", "unknown-sid")
                logger.info("Twilio SMS successfully queued. SID: %s", sid)
                return SMSDispatchResult(success=True, provider="twilio", message_id=sid)
            else:
                logger.error("Twilio SMS delivery failed: HTTP %s: %s", resp.status_code, resp.text)
                raise SMSDeliveryError(f"Twilio delivery failed: {resp.text}")
        except requests.RequestException as exc:
            logger.error("Twilio connection error: %s", exc)
            raise SMSDeliveryError(f"Twilio connection failure: {exc}")

    def _send_via_fast2sms(self, to_number: str, otp: str) -> SMSDispatchResult:
        """
        Sends custom OTP via Fast2SMS Indian SMS Gateway following official documentation:
        https://docs.fast2sms.com/reference/send-otp
        Supports:
        1. Official Send OTP API (/dev/otp/send) with custom OTP and otp_id.
        2. DLT bulk route (/dev/bulkV2 with route=dlt) when sender_id and message_id are configured.
        3. Quick SMS route (/dev/bulkV2 with route=q) when fast2sms_route=q.
        4. Bulk OTP route fallback (/dev/bulkV2 with route=otp).
        """
        # Ensure fresh configuration
        self.reload_config()

        # Extract strict 10-digit Indian mobile number
        clean_10 = re.sub(r"^\+91", "", to_number)
        clean_10 = re.sub(r"[^\d]", "", clean_10)

        if len(clean_10) != 10 or not clean_10.startswith(('6', '7', '8', '9')):
            raise SMSDeliveryError(f"Invalid 10-digit Indian mobile number for Fast2SMS: {clean_10}")

        headers = {
            "Authorization": self.fast2sms_api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        # Strategy 1: Official Fast2SMS Send OTP API (https://docs.fast2sms.com/reference/send-otp)
        # Uses application-generated 6-digit OTP while Fast2SMS handles carrier delivery
        if self.fast2sms_otp_id:
            url = "https://www.fast2sms.com/dev/otp/send"
            payload = {
                "mobile": clean_10,
                "otp_id": self.fast2sms_otp_id,
                "otp": otp,  # Custom 6-digit OTP generated by application
                "otp_expiry": 5,
            }
            try:
                resp = requests.post(url, json=payload, headers=headers, timeout=12)
                res_json = resp.json() if "application/json" in resp.headers.get("Content-Type", "") else {}
                if resp.status_code == 200 and res_json.get("return") is True:
                    req_id = res_json.get("request_id", "f2s-otp-ok")
                    logger.info("Fast2SMS OTP successfully queued via /dev/otp/send. Request ID: %s", req_id)
                    return SMSDispatchResult(success=True, provider="fast2sms", message_id=str(req_id))
                else:
                    err_msg = res_json.get("message") or resp.text
                    logger.error("Fast2SMS Smart OTP rejected [HTTP %s]: %s", resp.status_code, err_msg)
                    raise SMSDeliveryError(f"Fast2SMS error: {err_msg}")
            except requests.RequestException as exc:
                logger.error("Fast2SMS connection error: %s", exc)
                raise SMSDeliveryError(f"Fast2SMS connection failure: {exc}")

        # Strategy 2: DLT-approved template route via /dev/bulkV2
        if self.fast2sms_sender_id and self.fast2sms_message_id:
            url = "https://www.fast2sms.com/dev/bulkV2"
            payload = {
                "route": "dlt",
                "sender_id": self.fast2sms_sender_id,
                "message": self.fast2sms_message_id,
                "variables_values": otp,
                "numbers": clean_10,
            }
            try:
                resp = requests.post(url, json=payload, headers=headers, timeout=12)
                res_json = resp.json() if "application/json" in resp.headers.get("Content-Type", "") else {}
                if resp.status_code == 200 and res_json.get("return") is True:
                    req_id = res_json.get("request_id", "f2s-dlt-ok")
                    logger.info("Fast2SMS DLT SMS successfully dispatched. Request ID: %s", req_id)
                    return SMSDispatchResult(success=True, provider="fast2sms", message_id=str(req_id))
                else:
                    err_msg = res_json.get("message") or resp.text
                    logger.error("Fast2SMS DLT rejected [HTTP %s]: %s", resp.status_code, err_msg)
                    raise SMSDeliveryError(f"Fast2SMS DLT error: {err_msg}")
            except requests.RequestException as exc:
                logger.error("Fast2SMS connection error: %s", exc)
                raise SMSDeliveryError(f"Fast2SMS connection failure: {exc}")

        # Strategy 3: Quick SMS route (https://docs.fast2sms.com/reference/quick-sms-post)
        if self.fast2sms_route == "q":
            url = "https://www.fast2sms.com/dev/bulkV2"
            payload = {
                "route": "q",
                "message": f"Your Paddy Farming Assistant verification code is {otp}. Valid for 5 minutes.",
                "language": "english",
                "numbers": clean_10,
            }
            try:
                resp = requests.post(url, json=payload, headers=headers, timeout=12)
                res_json = resp.json() if "application/json" in resp.headers.get("Content-Type", "") else {}
                if resp.status_code == 200 and res_json.get("return") is True:
                    req_id = res_json.get("request_id", "f2s-q-ok")
                    logger.info("Fast2SMS Quick SMS successfully dispatched. Request ID: %s", req_id)
                    return SMSDispatchResult(success=True, provider="fast2sms", message_id=str(req_id))
                else:
                    err_msg = res_json.get("message") or resp.text
                    logger.error("Fast2SMS Quick SMS rejected [HTTP %s]: %s", resp.status_code, err_msg)
                    raise SMSDeliveryError(f"Fast2SMS Quick SMS error: {err_msg}")
            except requests.RequestException as exc:
                logger.error("Fast2SMS connection error: %s", exc)
                raise SMSDeliveryError(f"Fast2SMS connection failure: {exc}")

        # Strategy 4: Fallback to bulkV2 route=otp (GET)
        url = "https://www.fast2sms.com/dev/bulkV2"
        params = {
            "authorization": self.fast2sms_api_key,
            "route": "otp",
            "variables_values": otp,
            "numbers": clean_10,
        }
        try:
            resp = requests.get(url, params=params, timeout=12)
            res_json = resp.json() if "application/json" in resp.headers.get("Content-Type", "") else {}
            if resp.status_code == 200 and res_json.get("return") is True:
                req_id = res_json.get("request_id", "f2s-ok")
                logger.info("Fast2SMS OTP successfully dispatched. Request ID: %s", req_id)
                return SMSDispatchResult(success=True, provider="fast2sms", message_id=str(req_id))
            else:
                raw_msg = res_json.get("message") or resp.text
                if isinstance(raw_msg, list):
                    raw_msg = ", ".join(raw_msg)
                logger.error("Fast2SMS error response [HTTP %s]: %s", resp.status_code, raw_msg)
                
                # If Fast2SMS asks for OTP Message menu or DLT, give clear guidance
                if "complete website verification" in str(raw_msg).lower() or "otp message menu" in str(raw_msg).lower():
                    hint = "Fast2SMS requires website verification or an approved Smart OTP Template ID. Please configure FAST2SMS_OTP_ID from Fast2SMS Dashboard -> Smart OTP."
                    raise SMSDeliveryError(f"{raw_msg}. ({hint})")
                raise SMSDeliveryError(f"Fast2SMS error: {raw_msg}")
        except requests.RequestException as exc:
            logger.error("Fast2SMS connection error: %s", exc)
            raise SMSDeliveryError(f"Fast2SMS connection failure: {exc}")

    def _send_via_msg91(self, to_number: str, otp: str) -> SMSDispatchResult:
        """Sends OTP via MSG91 Gateway."""
        url = "https://control.msg91.com/api/v5/otp"
        clean_num = to_number.lstrip("+")
        params = {
            "template_id": self.msg91_template_id,
            "mobile": clean_num,
            "authkey": self.msg91_auth_key,
            "otp": otp,
        }

        try:
            resp = requests.get(url, params=params, timeout=12)
            if resp.status_code == 200:
                res_json = resp.json()
                if res_json.get("type") == "success":
                    msg_id = res_json.get("message", "msg91-ok")
                    logger.info("MSG91 successfully dispatched. ID: %s", msg_id)
                    return SMSDispatchResult(success=True, provider="msg91", message_id=str(msg_id))
                else:
                    raise SMSDeliveryError(f"MSG91 error: {res_json.get('message')}")
            else:
                raise SMSDeliveryError(f"MSG91 HTTP error {resp.status_code}: {resp.text}")
        except requests.RequestException as exc:
            raise SMSDeliveryError(f"MSG91 connection failure: {exc}")

    def _send_via_generic(self, to_number: str, text: str, otp: str) -> SMSDispatchResult:
        """Sends OTP via generic configurable webhook or custom gateway URL."""
        headers = {"Content-Type": "application/json"}
        if self.sms_gateway_api_key:
            headers["Authorization"] = f"Bearer {self.sms_gateway_api_key}"

        payload = {
            "mobile": to_number,
            "message": text,
            "otp": otp,
        }

        try:
            if self.sms_gateway_method == "GET":
                resp = requests.get(self.sms_gateway_url, params=payload, headers=headers, timeout=12)
            else:
                resp = requests.post(self.sms_gateway_url, json=payload, headers=headers, timeout=12)

            if resp.status_code in (200, 201, 202):
                return SMSDispatchResult(success=True, provider="generic", message_id="generic-ok")
            else:
                raise SMSDeliveryError(f"Generic gateway returned HTTP {resp.status_code}: {resp.text}")
        except requests.RequestException as exc:
            raise SMSDeliveryError(f"Generic gateway connection failure: {exc}")

    def get_last_dev_otp(self, mobile_number: Optional[str] = None) -> Optional[str]:
        """Utility for test suites to inspect the latest OTP dispatched in dev/test mode."""
        if not self._sent_messages:
            return None
        if mobile_number:
            for item in reversed(self._sent_messages):
                if item["mobile"] == mobile_number:
                    return item["otp"]
            return None
        return self._sent_messages[-1]["otp"]

    def clear_dev_messages(self) -> None:
        """Clears in-memory test message cache."""
        self._sent_messages.clear()


# Global singleton instance
sms_service = SMSService()

