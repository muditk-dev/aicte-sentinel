from typing import List, Optional, TYPE_CHECKING
from sqlalchemy import String, Integer, Boolean, Text, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.models.base import UUIDPrimaryKeyMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.application import Application
    from app.models.institution import Institution
    from app.models.user import User
    from app.models.evc import Expert


class Committee(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "committees"

    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    
    # SHC (Standing Hearing Committee), SAC (Standing Appellate Committee)
    committee_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    quorum_required: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    valid_from: Mapped[str] = mapped_column(String(50), nullable=False)
    valid_to: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Relationships
    memberships: Mapped[List["CommitteeMembership"]] = relationship(
        "CommitteeMembership", back_populates="committee", cascade="all, delete-orphan", lazy="selectin"
    )
    hearings: Mapped[List["Hearing"]] = relationship(
        "Hearing", back_populates="committee", cascade="all, delete-orphan"
    )


class CommitteeMembership(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "committee_memberships"

    committee_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("committees.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    expert_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("experts.id", ondelete="SET NULL"), nullable=True, index=True
    )
    member_name: Mapped[str] = mapped_column(String(150), nullable=False)
    
    # CHAIRPERSON, MEMBER_SECRETARY, LEGAL_EXPERT, ACADEMIC_EXPERT, MEMBER
    member_role: Mapped[str] = mapped_column(String(50), default="MEMBER", nullable=False)
    conflict_declarations_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    committee: Mapped["Committee"] = relationship("Committee", back_populates="memberships")
    user: Mapped[Optional["User"]] = relationship("User")
    expert: Mapped[Optional["Expert"]] = relationship("Expert")


class Hearing(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "hearings"

    committee_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("committees.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    hearing_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    
    # SHC, SAC
    hearing_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    
    # DRAFT -> SCHEDULED -> NOTICE_ISSUED -> IN_SESSION -> MINUTES_PENDING -> RECOMMENDATION_RECORDED -> COMPLETED
    # Exception states: POSTPONED, CANCELLED
    status: Mapped[str] = mapped_column(String(50), default="SCHEDULED", nullable=False, index=True)
    
    scheduled_date: Mapped[str] = mapped_column(String(50), nullable=False)
    meeting_mode: Mapped[str] = mapped_column(String(50), default="HYBRID", nullable=False)
    venue_or_link: Mapped[str] = mapped_column(String(500), nullable=False)
    agenda: Mapped[str] = mapped_column(Text, nullable=False)
    
    postponement_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    cancellation_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    chairperson_name: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    conducted_at: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    
    # Minutes and Advisory Recommendation (Non-automatic)
    minutes_of_meeting: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    final_recommendation: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    recommendation_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    committee: Mapped["Committee"] = relationship("Committee", back_populates="hearings")
    dockets: Mapped[List["HearingDocket"]] = relationship(
        "HearingDocket", back_populates="hearing", cascade="all, delete-orphan"
    )
    attendances: Mapped[List["HearingAttendance"]] = relationship(
        "HearingAttendance", back_populates="hearing", cascade="all, delete-orphan"
    )


class HearingDocket(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "hearing_dockets"
    __table_args__ = (
        UniqueConstraint("hearing_id", "application_id", name="uq_hearing_application_docket"),
    )

    hearing_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("hearings.id", ondelete="CASCADE"), nullable=False, index=True
    )
    application_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("applications.id", ondelete="CASCADE"), nullable=False, index=True
    )
    institution_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    docket_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    matter_summary: Mapped[str] = mapped_column(Text, nullable=False)
    referred_by: Mapped[str] = mapped_column(String(100), default="REGIONAL_OFFICE", nullable=False)
    institutional_representative_name: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    
    # PENDING, HEARD, ADJOURNED, DECIDED
    docket_status: Mapped[str] = mapped_column(String(50), default="PENDING", nullable=False, index=True)
    docket_recommendation: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    docket_remarks: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    hearing: Mapped["Hearing"] = relationship("Hearing", back_populates="dockets")
    application: Mapped["Application"] = relationship("Application")
    institution: Mapped["Institution"] = relationship("Institution")


class HearingAttendance(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "hearing_attendances"

    hearing_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("hearings.id", ondelete="CASCADE"), nullable=False, index=True
    )
    member_name: Mapped[str] = mapped_column(String(150), nullable=False)
    member_role: Mapped[str] = mapped_column(String(50), nullable=False)
    user_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    attended: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    attendance_mode: Mapped[str] = mapped_column(String(50), default="IN_PERSON", nullable=False)
    conflict_declared_for_docket_ids: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    hearing: Mapped["Hearing"] = relationship("Hearing", back_populates="attendances")
