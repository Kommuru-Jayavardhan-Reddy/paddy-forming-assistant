"""
Paddy Farming Assistant - Prediction Repository (STEP 11F.8)
Handles asynchronous CRUD operations for AI disease diagnosis inferences.
"""

import logging
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional, List, Dict, Any, Tuple, Sequence
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.prediction import PredictionHistory
from app.db.repositories.base import BaseRepository

logger = logging.getLogger(__name__)


class PredictionRepository(BaseRepository[PredictionHistory]):
    """
    Asynchronous repository for AI disease classification inference history.
    """

    def __init__(self, session: AsyncSession):
        super().__init__(PredictionHistory, session)

    def validate_prediction_inputs(
        self,
        prediction_mode: str,
        predicted_class_index: int,
        confidence: float,
    ) -> None:
        """
        Validates model-specific class indices and probability ranges before database submission.
        Raises ValueError if inputs violate constraints.
        """
        if prediction_mode not in ("image_only", "multimodal"):
            raise ValueError(
                f"Invalid prediction_mode '{prediction_mode}': must be 'image_only' or 'multimodal'."
            )

        if not (0.0 <= confidence <= 1.0):
            raise ValueError(f"Confidence score {confidence} is outside valid [0.0, 1.0] range.")

        if prediction_mode == "image_only":
            if not (0 <= predicted_class_index <= 12):
                raise ValueError(
                    f"Image-only predicted_class_index {predicted_class_index} is outside valid [0, 12] range."
                )
        elif prediction_mode == "multimodal":
            if not (0 <= predicted_class_index <= 10):
                raise ValueError(
                    f"Multimodal predicted_class_index {predicted_class_index} is outside valid [0, 10] range."
                )

    async def create_prediction(
        self,
        prediction_mode: str,
        model_name: str,
        model_version: str,
        predicted_disease: str,
        predicted_class_index: int,
        confidence: float,
        is_healthy: bool,
        top_k_predictions: List[Dict[str, Any]],
        field_id: Optional[uuid.UUID] = None,
        low_confidence: bool = False,
        attention_weights: Optional[List[float]] = None,
        image_storage_path: Optional[str] = None,
        image_sha256: Optional[str] = None,
        gradcam_storage_path: Optional[str] = None,
        farmer_question: Optional[str] = None,
        response_language: str = "en",
        inference_latency_ms: Optional[float] = None,
        device: str = "cpu",
    ) -> PredictionHistory:
        """
        Creates, validates, and persists a new diagnostic prediction inference log.
        """
        self.validate_prediction_inputs(
            prediction_mode=prediction_mode,
            predicted_class_index=predicted_class_index,
            confidence=confidence,
        )

        record = PredictionHistory(
            field_id=field_id,
            prediction_mode=prediction_mode,
            model_name=model_name,
            model_version=model_version,
            predicted_disease=predicted_disease,
            predicted_class_index=predicted_class_index,
            confidence=Decimal(str(round(confidence, 4))),
            is_healthy=is_healthy,
            low_confidence=low_confidence or (confidence < 0.60),
            top_k_predictions=top_k_predictions,
            attention_weights=attention_weights,
            image_storage_path=image_storage_path,
            image_sha256=image_sha256,
            gradcam_storage_path=gradcam_storage_path,
            farmer_question=farmer_question,
            response_language=response_language,
            inference_latency_ms=Decimal(str(round(inference_latency_ms, 2))) if inference_latency_ms is not None else None,
            device=device,
        )

        self.session.add(record)
        await self.session.flush()
        return record

    async def list_predictions(
        self,
        prediction_id: Optional[uuid.UUID] = None,
        field_id: Optional[uuid.UUID] = None,
        prediction_mode: Optional[str] = None,
        disease: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[Sequence[PredictionHistory], int]:
        """
        Lists past predictions with pagination and optional filtering by:
        - prediction_id: UUID of specific prediction
        - field_id: UUID of linked field
        - prediction_mode: 'image_only' or 'multimodal'
        - disease: predicted disease name (case-insensitive)
        - start_date: UTC timestamp lower bound
        - end_date: UTC timestamp upper bound
        Ordered by created_at DESC.
        """
        safe_limit = min(max(1, limit), 200)
        safe_skip = max(0, skip)

        query = select(PredictionHistory)
        count_query = select(func.count(PredictionHistory.id))

        if prediction_id is not None:
            query = query.where(PredictionHistory.id == prediction_id)
            count_query = count_query.where(PredictionHistory.id == prediction_id)

        if field_id is not None:
            query = query.where(PredictionHistory.field_id == field_id)
            count_query = count_query.where(PredictionHistory.field_id == field_id)

        if prediction_mode is not None:
            query = query.where(PredictionHistory.prediction_mode == prediction_mode)
            count_query = count_query.where(PredictionHistory.prediction_mode == prediction_mode)

        if disease is not None and disease.strip():
            norm_disease = disease.strip().lower()
            query = query.where(func.lower(PredictionHistory.predicted_disease) == norm_disease)
            count_query = count_query.where(func.lower(PredictionHistory.predicted_disease) == norm_disease)

        if start_date is not None:
            query = query.where(PredictionHistory.created_at >= start_date)
            count_query = count_query.where(PredictionHistory.created_at >= start_date)

        if end_date is not None:
            query = query.where(PredictionHistory.created_at <= end_date)
            count_query = count_query.where(PredictionHistory.created_at <= end_date)

        query = query.order_by(desc(PredictionHistory.created_at)).offset(safe_skip).limit(safe_limit)

        total_res = await self.session.execute(count_query)
        total_count = total_res.scalar() or 0

        res = await self.session.execute(query)
        records = res.scalars().all()

        return records, total_count
