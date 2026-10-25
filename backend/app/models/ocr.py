from datetime import datetime
from typing import Optional, List
from sqlalchemy import String, Text, Float, Integer, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.models.base import UUIDPrimaryKeyMixin, TimestampMixin


class OCRJob(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "ocr_jobs"

    document_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    application_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("applications.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(String(30), default="QUEUED", nullable=False, index=True)  # QUEUED, PROCESSING, COMPLETED, FAILED
    engine: Mapped[str] = mapped_column(String(50), default="pypdf_extractor", nullable=False)
    page_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    extracted_text_preview: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    processing_time_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    fields: Mapped[List["OCRExtractedField"]] = relationship(
        "OCRExtractedField", back_populates="ocr_job", cascade="all, delete-orphan", lazy="selectin"
    )


class OCRExtractedField(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "ocr_extracted_fields"

    ocr_job_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("ocr_jobs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    document_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    application_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("applications.id", ondelete="CASCADE"), nullable=False, index=True
    )

    field_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    field_category: Mapped[str] = mapped_column(String(50), nullable=False, index=True)  # FIRE_NOC, LAND_TITLE, BUILDING_PLAN, FINANCIAL, GENERAL
    raw_value: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    confidence: Mapped[float] = mapped_column(Float, default=0.90, nullable=False)
    page_number: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    bounding_box_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Verification workflow: PENDING, VERIFIED, REJECTED, CORRECTED
    verification_status: Mapped[str] = mapped_column(String(30), default="PENDING", nullable=False, index=True)
    is_automated_advisory: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    corrected_value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    review_comments: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    reviewed_by_user_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    ocr_job: Mapped["OCRJob"] = relationship("OCRJob", back_populates="fields")
