from typing import Optional, List
from sqlalchemy import String, Text, Float, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.models.base import UUIDPrimaryKeyMixin, TimestampMixin


class ModelVersion(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "model_versions"

    name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    version_tag: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    algorithm: Mapped[str] = mapped_column(String(100), nullable=False)
    features_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    metrics_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    training_dataset_summary: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    artifact_path: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    predictions: Mapped[List["DelayRiskPrediction"]] = relationship(
        "DelayRiskPrediction", back_populates="model_version", cascade="all, delete-orphan"
    )


class DelayRiskPrediction(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "delay_risk_predictions"

    application_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("applications.id", ondelete="CASCADE"), nullable=False, index=True
    )
    model_version_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("model_versions.id", ondelete="SET NULL"), nullable=True, index=True
    )

    risk_score: Mapped[float] = mapped_column(Float, nullable=False)  # 0.0 to 1.0
    risk_category: Mapped[str] = mapped_column(String(20), nullable=False, index=True)  # LOW, MEDIUM, HIGH, CRITICAL
    estimated_delay_days: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    confidence_score: Mapped[float] = mapped_column(Float, default=0.85, nullable=False)

    # Explainable factor attributions (SHAP style breakdown)
    factor_attributions_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)

    # Statutory Non-Binding Notice
    is_automated_advisory: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    advisory_notes: Mapped[str] = mapped_column(
        Text,
        default="AICTE Statutory Rule: This delay-risk prediction is purely automated intelligence to assist scheduling and resource allocation. It does not determine statutory compliance, approval, or rejection.",
        nullable=False,
    )

    model_version: Mapped[Optional["ModelVersion"]] = relationship("ModelVersion", back_populates="predictions")
