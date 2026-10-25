from typing import List, Optional, TYPE_CHECKING
from sqlalchemy import String, Integer, Boolean, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.models.base import UUIDPrimaryKeyMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.application import Application
    from app.models.institution import Institution
    from app.models.user import User


class StatutoryDecision(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "statutory_decisions"

    application_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("applications.id", ondelete="CASCADE"), nullable=False, index=True
    )
    institution_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    decision_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    
    # APPROVED, CONDITIONALLY_APPROVED, REJECTED, RETURNED_FOR_REVIEW
    decision_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    academic_year: Mapped[str] = mapped_column(String(20), default="2026-2027", nullable=False)
    
    # Statutory authority level: REGIONAL_OFFICER, SUPER_ADMIN, COUNCIL_MEMBER
    authority_role: Mapped[str] = mapped_column(String(50), nullable=False)
    authorized_by_user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    authorized_at: Mapped[str] = mapped_column(String(50), nullable=False)
    governing_policy_version: Mapped[str] = mapped_column(String(50), default="AICTE-APH-2026-V1", nullable=False)
    
    reasons: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_references_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    intake_approved: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    valid_for_years: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    
    # Immutability and Reconsideration
    is_final: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_reconsidered: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    reconsideration_reference: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # Non-repudiation cryptographic digest & human officer attestation
    sha256_attestation: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    declaration_text: Mapped[str] = mapped_column(Text, nullable=False)

    # Relationships
    application: Mapped["Application"] = relationship("Application")
    institution: Mapped["Institution"] = relationship("Institution")
    authorized_by: Mapped["User"] = relationship("User")
    conditions: Mapped[List["DecisionCondition"]] = relationship(
        "DecisionCondition", back_populates="decision", cascade="all, delete-orphan"
    )


class DecisionCondition(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "decision_conditions"

    decision_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("statutory_decisions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    condition_code: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    due_date: Mapped[str] = mapped_column(String(50), nullable=False)
    
    # PENDING, COMPLIED, DEFAULTED
    compliance_status: Mapped[str] = mapped_column(String(50), default="PENDING", nullable=False, index=True)

    decision: Mapped["StatutoryDecision"] = relationship("StatutoryDecision", back_populates="conditions")
