"""
Paddy Farming Assistant - Report ORM Model (STEP 11F.5)
Registry of compiled farmer diagnostic reports, vegetation health summaries, and advisory dossiers.
"""

import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any, TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    String,
    Text,
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
    from app.db.models.prediction import PredictionHistory


class Report(Base):
    """
    Compiled diagnostic report, field vegetation summary, or market advisory dossier.
    Stores safe filesystem paths and JSON metadata rather than raw binary blobs in PostgreSQL.
    """
    __tablename__ = "reports"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
        comment="Unique report document identifier",
    )
    field_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("fields.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Associated agricultural parcel (nullable if generated for standalone leaf)",
    )
    prediction_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("prediction_history.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Associated disease prediction run (nullable for purely satellite/market reports)",
    )
    report_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Report category: 'disease_diagnostic', 'field_health_summary', 'seasonal_advisory', 'market_intelligence'",
    )
    title: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        comment="Human-readable title of the compiled report",
    )
    summary: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Executive summary of key agronomic findings and advisories",
    )
    status: Mapped[str] = mapped_column(
        String(20),
        default="completed",
        server_default=text("'completed'"),
        nullable=False,
        comment="Document generation status: 'generating', 'completed', or 'failed'",
    )
    file_path: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Safe relative storage path to generated document on disk (never raw binary)",
    )
    file_format: Mapped[str] = mapped_column(
        String(10),
        default="pdf",
        server_default=text("'pdf'"),
        nullable=False,
        comment="File MIME/extension format (e.g. 'pdf', 'html', 'json')",
    )
    file_size_bytes: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        nullable=True,
        comment="File size on disk in bytes",
    )
    report_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Detailed parameter inputs, model versions, and index metrics used in compilation",
    )
    generated_by: Mapped[str] = mapped_column(
        String(50),
        default="system",
        server_default=text("'system'"),
        nullable=False,
        comment="Actor or process that initiated report compilation",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
        comment="Report generation timestamp in UTC",
    )

    # Relationships
    field: Mapped[Optional["Field"]] = relationship(
        "Field",
        back_populates="reports",
    )
    prediction: Mapped[Optional["PredictionHistory"]] = relationship(
        "PredictionHistory",
        back_populates="reports",
    )

    __table_args__ = (
        CheckConstraint(
            "report_type IN ('disease_diagnostic', 'field_health_summary', 'seasonal_advisory', 'market_intelligence')",
            name="ck_report_type",
        ),
        CheckConstraint(
            "status IN ('generating', 'completed', 'failed')",
            name="ck_report_status",
        ),
        Index("idx_reports_field_created", "field_id", "created_at"),
        Index("idx_reports_type_created", "report_type", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<Report(id={self.id}, type='{self.report_type}', title='{self.title}', status='{self.status}')>"
