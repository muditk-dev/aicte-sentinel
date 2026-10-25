from datetime import datetime
from typing import List, Optional, TYPE_CHECKING
from sqlalchemy import String, Integer, Boolean, Text, DateTime, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.models.base import UUIDPrimaryKeyMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.institution import Institution
    from app.models.application import Application
    from app.models.decision import StatutoryDecision
    from app.models.user import User
    from app.models.document import Document
    from app.models.deficiency import Notification


class ComplianceObligation(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Persistent, configurable post-approval compliance obligation.
    Associated with approved institutions and statutory decision orders.
    Valid states: PENDING, SUBMITTED, UNDER_REVIEW, COMPLIANT, DEFICIENT, OVERDUE, CLOSED.
    """
    __tablename__ = "compliance_obligations"

    obligation_code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    institution_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    application_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("applications.id", ondelete="SET NULL"), nullable=True, index=True
    )
    decision_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("statutory_decisions.id", ondelete="SET NULL"), nullable=True, index=True
    )
    
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Category: FACULTY_RATIO, SAFETY_CLEARANCE, INFRASTRUCTURE, AFFILIATION, FINANCIAL_DISCLOSURE, ANNUAL_REPORT, GENERAL
    category: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    
    # Traceable statutory source (e.g., APH 2026-27 Clause 4.1.1)
    source_reference: Mapped[str] = mapped_column(String(255), nullable=False)
    applicability: Mapped[str] = mapped_column(String(100), default="ALL_TECHNICAL_INSTITUTIONS", nullable=False)
    
    assigned_officer_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    
    # Statutory timelines (stored as timezone-aware datetimes)
    issue_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    due_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    
    # Recurrence: ONE_TIME, ANNUAL, BIENNIAL, QUARTERLY
    recurrence: Mapped[str] = mapped_column(String(50), default="ONE_TIME", nullable=False)
    
    # Lifecycle: PENDING, SUBMITTED, UNDER_REVIEW, COMPLIANT, DEFICIENT, OVERDUE, CLOSED
    status: Mapped[str] = mapped_column(String(50), default="PENDING", nullable=False, index=True)
    
    # Demonstration & Governance
    is_synthetic_demonstration: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_automated_advisory: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_by_user_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # Relationships
    institution: Mapped["Institution"] = relationship("Institution", lazy="selectin")
    application: Mapped[Optional["Application"]] = relationship("Application", lazy="selectin")
    decision: Mapped[Optional["StatutoryDecision"]] = relationship("StatutoryDecision", lazy="selectin")
    assigned_officer: Mapped[Optional["User"]] = relationship(
        "User", foreign_keys=[assigned_officer_id], lazy="selectin"
    )
    closed_by: Mapped[Optional["User"]] = relationship(
        "User", foreign_keys=[closed_by_user_id], lazy="selectin"
    )
    
    evidences: Mapped[List["ObligationEvidence"]] = relationship(
        "ObligationEvidence", back_populates="obligation", cascade="all, delete-orphan", lazy="selectin"
    )
    history: Mapped[List["ObligationReviewHistory"]] = relationship(
        "ObligationReviewHistory", back_populates="obligation", cascade="all, delete-orphan", lazy="selectin"
    )
    escalations: Mapped[List["ComplianceEscalation"]] = relationship(
        "ComplianceEscalation", back_populates="obligation", cascade="all, delete-orphan", lazy="selectin"
    )

    __table_args__ = (
        Index("ix_obligations_inst_status", "institution_id", "status"),
        Index("ix_obligations_due_status", "due_date", "status"),
    )


class ObligationEvidence(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Supporting evidence uploaded by institutions for a post-approval compliance obligation.
    """
    __tablename__ = "obligation_evidences"

    obligation_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("compliance_obligations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    document_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("documents.id", ondelete="SET NULL"), nullable=True, index=True
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    file_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    sha256_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    uploaded_by_user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    submission_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    obligation: Mapped["ComplianceObligation"] = relationship("ComplianceObligation", back_populates="evidences")
    document: Mapped[Optional["Document"]] = relationship("Document", lazy="selectin")
    uploaded_by: Mapped["User"] = relationship("User", lazy="selectin")


class ObligationReviewHistory(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Immutable audit history of status transitions and officer review determinations for obligations.
    """
    __tablename__ = "obligation_review_history"

    obligation_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("compliance_obligations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    actor_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    actor_role: Mapped[str] = mapped_column(String(50), nullable=False)
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    # Action types: CREATED, ASSIGNED, EVIDENCE_SUBMITTED, REVIEW_STARTED, VERIFIED_COMPLIANT, DEFICIENCY_FLAGGED, RESUBMITTED, OVERDUE_TRANSITION, CLOSED
    previous_status: Mapped[str] = mapped_column(String(50), nullable=False)
    new_status: Mapped[str] = mapped_column(String(50), nullable=False)
    comments: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    obligation: Mapped["ComplianceObligation"] = relationship("ComplianceObligation", back_populates="history")
    actor: Mapped["User"] = relationship("User", lazy="selectin")


class ComplianceEscalation(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Records overdue escalation events and notifications triggered by the compliance monitoring engine.
    Level 1: Regional Officer escalation (> 7 days overdue).
    Level 2: Central Authority / Super Admin escalation (> 14 days overdue).
    """
    __tablename__ = "compliance_escalations"

    obligation_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("compliance_obligations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    institution_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    escalation_level: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    severity: Mapped[str] = mapped_column(String(50), default="HIGH", nullable=False)  # MEDIUM, HIGH, CRITICAL
    trigger_reason: Mapped[str] = mapped_column(String(100), nullable=False)  # OVERDUE_7_DAYS, OVERDUE_14_DAYS, REPEATED_DEFICIENCY
    days_overdue: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    notified_roles_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    notification_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("notifications.id", ondelete="SET NULL"), nullable=True
    )
    is_resolved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_by_user_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    resolution_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    obligation: Mapped["ComplianceObligation"] = relationship("ComplianceObligation", back_populates="escalations")
    institution: Mapped["Institution"] = relationship("Institution", lazy="selectin")
    resolved_by: Mapped[Optional["User"]] = relationship("User", foreign_keys=[resolved_by_user_id], lazy="selectin")
