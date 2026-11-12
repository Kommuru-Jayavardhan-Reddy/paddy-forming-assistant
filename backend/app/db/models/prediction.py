"""
Paddy Farming Assistant - PredictionHistory ORM Model (STEP 11F.5)
Stores diagnostic inference records from image-only (13 classes) and multimodal (11 classes) AI models.
"""

import uuid
from decimal import Decimal
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, TYPE_CHECKING

from sqlalchemy import (
    String,
    Text,
    Numeric,
    Integer,
    Boolean,
    DateTime,
    ForeignKey,
    CheckConstraint,
    Index,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.field import Field
    from app.db.models.report import Report
    from app.db.models.farmer import Farmer


class PredictionHistory(Base):
    """
    Historical log of disease classification inferences.
    Maintains rigorous separation between 13-class image predictions
    and 11-class multimodal cross-attention predictions.
    """
    __tablename__ = "prediction_history"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
        comment="Unique inference prediction ID",
    )
    field_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("fields.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Optional foreign key to field parcel (nullable for standalone leaf photos)",
    )
    farmer_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("farmers.id", ondelete="SET NULL"),
        nullable=True,
        comment="Owner farmer UUID for dashboard isolation (nullable for standalone/legacy predictions)",
    )
    prediction_mode: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="Inference mode: 'image_only' (13 classes) or 'multimodal' (11 classes)",
    )
    model_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Model architecture name (e.g. EfficientNet-B4 or TemporalCrossAttention)",
    )
    model_version: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Model checkpoint artifact identifier (e.g. phaseC_best or step7L_controlled_best)",
    )
    predicted_disease: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        comment="Top predicted disease classification label",
    )
    predicted_class_index: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Model output logit index (0-12 for image_only, 0-10 for multimodal)",
    )
    confidence: Mapped[Decimal] = mapped_column(
        Numeric(5, 4),
        nullable=False,
        comment="Top prediction softmax probability score [0.0000 - 1.0000]",
    )
    is_healthy: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default=text("false"),
        nullable=False,
        comment="Flag indicating whether top predicted class is 'normal' (healthy leaf)",
    )
    low_confidence: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default=text("false"),
        nullable=False,
        comment="Flag indicating confidence below advisory threshold (< 0.60)",
    )
    top_k_predictions: Mapped[List[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=text("'[]'::jsonb"),
        comment="JSONB array of candidate predictions: [{'disease': ..., 'probability': ..., 'index': ...}]",
    )
    attention_weights: Mapped[Optional[List[float]]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Normalized cross-attention weights across the 10 satellite timesteps (multimodal only)",
    )
    image_storage_path: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Relative storage path or object URI of the input leaf image (never absolute paths)",
    )
    image_sha256: Mapped[Optional[str]] = mapped_column(
        String(64),
        nullable=True,
        index=True,
        comment="SHA-256 hash of the input image for deduplication and provenance",
    )
    gradcam_storage_path: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Relative path to saved Grad-CAM heatmap visualization overlay",
    )
    farmer_question: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Optional farmer natural language query submitted with prediction",
    )
    response_language: Mapped[str] = mapped_column(
        String(10),
        default="en",
        server_default=text("'en'"),
        nullable=False,
        comment="Language requested for advisory responses (e.g. 'en', 'te')",
    )
    inference_latency_ms: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(7, 2),
        nullable=True,
        comment="Wall-clock inference latency in milliseconds",
    )
    device: Mapped[str] = mapped_column(
        String(20),
        default="cpu",
        server_default=text("'cpu'"),
        nullable=False,
        comment="Hardware execution device utilized ('cpu' or 'cuda')",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
        comment="Inference timestamp in UTC",
    )

    # Relationships
    field: Mapped[Optional["Field"]] = relationship(
        "Field",
        back_populates="predictions",
    )
    reports: Mapped[List["Report"]] = relationship(
        "Report",
        back_populates="prediction",
        cascade="save-update, merge",
        passive_deletes=True,
    )
    farmer: Mapped[Optional["Farmer"]] = relationship(
        "Farmer",
        back_populates="predictions",
    )

    __table_args__ = (
        CheckConstraint(
            "prediction_mode IN ('image_only', 'multimodal')",
            name="ck_pred_mode",
        ),
        CheckConstraint(
            "confidence >= 0.0 AND confidence <= 1.0",
            name="ck_pred_confidence",
        ),
        # Class index safety: Enforce 0-12 for image_only and 0-10 for multimodal
        CheckConstraint(
            "(prediction_mode = 'image_only' AND predicted_class_index >= 0 AND predicted_class_index <= 12) OR "
            "(prediction_mode = 'multimodal' AND predicted_class_index >= 0 AND predicted_class_index <= 10)",
            name="ck_pred_mode_class_index",
        ),
        Index("idx_pred_field_created", "field_id", "created_at"),
        Index("idx_pred_farmer_created", "farmer_id", "created_at"),
        Index("idx_pred_mode_created", "prediction_mode", "created_at"),
        Index("idx_pred_topk_gin", "top_k_predictions", postgresql_using="gin"),
    )

    def __repr__(self) -> str:
        return f"<PredictionHistory(id={self.id}, mode='{self.prediction_mode}', disease='{self.predicted_disease}', conf={self.confidence})>"
