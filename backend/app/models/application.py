from typing import List, Optional, TYPE_CHECKING
from sqlalchemy import String, Text, Float, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.models.base import UUIDPrimaryKeyMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.institution import Institution
    from app.models.workflow import WorkflowTemplate, WorkflowVersion
    from app.models.user import User


class Application(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "applications"

    application_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    
    # Institution & Workflow link
    institution_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    template_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("workflow_templates.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    version_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("workflow_versions.id", ondelete="RESTRICT"), nullable=False, index=True
    )

    # Core Lifecycle Status
    current_status: Mapped[str] = mapped_column(String(50), default="DRAFT", nullable=False, index=True)
    academic_year: Mapped[str] = mapped_column(String(20), default="2026-2027", nullable=False)
    
    # Submission & Intake Details
    submission_data_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    submission_date: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    sla_deadline: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Assigned Officers
    applicant_user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    assigned_scrutiny_officer_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    assigned_regional_officer_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )

    # Explainable Delay-Risk Indicators (Advisory Only)
    delay_risk_score: Mapped[Optional[float]] = mapped_column(Float, default=0.0, nullable=True)
    delay_risk_factors_json: Mapped[Optional[str]] = mapped_column(Text, default="[]", nullable=True)

    # Relationships
    institution: Mapped["Institution"] = relationship("Institution", back_populates="applications")
    template: Mapped["WorkflowTemplate"] = relationship("WorkflowTemplate", back_populates="applications")
    version: Mapped["WorkflowVersion"] = relationship("WorkflowVersion", back_populates="applications")
    events: Mapped[List["ApplicationEvent"]] = relationship(
        "ApplicationEvent", back_populates="application", cascade="all, delete-orphan", order_by="ApplicationEvent.created_at"
    )


class ApplicationEvent(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "application_events"

    application_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("applications.id", ondelete="CASCADE"), nullable=False, index=True
    )
    actor_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    event_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    from_status: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    to_status: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    remarks: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    event_payload_json: Mapped[Optional[str]] = mapped_column(Text, default="{}", nullable=True)

    application: Mapped["Application"] = relationship("Application", back_populates="events")
    actor: Mapped["User"] = relationship("User", back_populates="events_created")
