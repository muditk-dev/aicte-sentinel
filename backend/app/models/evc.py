from typing import List, Optional, TYPE_CHECKING
from sqlalchemy import String, Integer, Float, Boolean, Text, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.models.base import UUIDPrimaryKeyMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.application import Application
    from app.models.institution import Institution
    from app.models.user import User


class Expert(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "experts"

    # Optional link to user account if expert has portal login
    user_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, unique=True, index=True
    )
    name: Mapped[str] = mapped_column(String(150), nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    designation: Mapped[str] = mapped_column(String(150), nullable=False)
    organization: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    
    # ACADEMIC, INDUSTRY, REGULATORY
    expert_type: Mapped[str] = mapped_column(String(50), default="ACADEMIC", nullable=False, index=True)
    qualifications: Mapped[str] = mapped_column(String(255), nullable=False)
    experience_years: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    specializations_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    
    # Conflict check inputs
    affiliated_institution_ids_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    alma_mater: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    state: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    district: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    
    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    verification_status: Mapped[str] = mapped_column(String(50), default="VERIFIED", nullable=False, index=True)
    availability_status: Mapped[str] = mapped_column(String(50), default="AVAILABLE", nullable=False, index=True)
    conflict_declarations_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)

    # Relationships
    user: Mapped[Optional["User"]] = relationship("User")
    inspection_assignments: Mapped[List["EVCInspectionExpert"]] = relationship(
        "EVCInspectionExpert", back_populates="expert", cascade="all, delete-orphan"
    )


class EVCInspection(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "evc_inspections"

    application_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("applications.id", ondelete="CASCADE"), nullable=False, index=True
    )
    institution_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    inspection_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    
    # PHYSICAL, VIRTUAL, HYBRID
    inspection_mode: Mapped[str] = mapped_column(String(50), default="PHYSICAL", nullable=False, index=True)
    
    # DRAFT -> SCHEDULED -> IN_PROGRESS -> REPORT_SUBMITTED -> UNDER_REVIEW -> ACCEPTED or RETURNED_FOR_CORRECTION
    status: Mapped[str] = mapped_column(String(50), default="SCHEDULED", nullable=False, index=True)
    
    scheduled_start_date: Mapped[str] = mapped_column(String(50), nullable=False)
    scheduled_end_date: Mapped[str] = mapped_column(String(50), nullable=False)
    actual_inspection_date: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    
    chairperson_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("experts.id", ondelete="SET NULL"), nullable=True
    )
    meeting_link: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    location_coordinates: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    location_address: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    cancellation_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    assigned_by_user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )

    # Relationships
    application: Mapped["Application"] = relationship("Application")
    institution: Mapped["Institution"] = relationship("Institution")
    assigned_by: Mapped["User"] = relationship("User")
    panel_members: Mapped[List["EVCInspectionExpert"]] = relationship(
        "EVCInspectionExpert", back_populates="inspection", cascade="all, delete-orphan"
    )
    report_versions: Mapped[List["EVCReportVersion"]] = relationship(
        "EVCReportVersion", back_populates="inspection", cascade="all, delete-orphan", order_by="EVCReportVersion.version_number.desc()"
    )


class EVCInspectionExpert(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "evc_inspection_experts"
    __table_args__ = (
        UniqueConstraint("inspection_id", "expert_id", name="uq_inspection_expert"),
    )

    inspection_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("evc_inspections.id", ondelete="CASCADE"), nullable=False, index=True
    )
    expert_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("experts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    
    # CHAIRPERSON, MEMBER, CONVENER, SPECIALIST
    role: Mapped[str] = mapped_column(String(50), default="MEMBER", nullable=False)
    conflict_check_passed: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    conflict_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Attendance: PENDING, PRESENT, ABSENT
    attendance_status: Mapped[str] = mapped_column(String(50), default="PENDING", nullable=False)
    attendance_timestamp: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    
    # Sign-off: PENDING, SIGNED, DISSENT
    sign_off_status: Mapped[str] = mapped_column(String(50), default="PENDING", nullable=False)
    sign_off_timestamp: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    sign_off_remarks: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    inspection: Mapped["EVCInspection"] = relationship("EVCInspection", back_populates="panel_members")
    expert: Mapped["Expert"] = relationship("Expert", back_populates="inspection_assignments")


class EVCReportVersion(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "evc_report_versions"
    __table_args__ = (
        UniqueConstraint("inspection_id", "version_number", name="uq_inspection_report_version"),
    )

    inspection_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("evc_inspections.id", ondelete="CASCADE"), nullable=False, index=True
    )
    version_number: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    application_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("applications.id", ondelete="CASCADE"), nullable=False, index=True
    )
    submitted_by_user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    submitted_at: Mapped[str] = mapped_column(String(50), nullable=False)
    sha256_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    
    # Overall Recommendation: RECOMMENDED, DEFICIENT, SERIOUS_VIOLATIONS
    overall_recommendation: Mapped[str] = mapped_column(String(50), nullable=False)
    infrastructure_score: Mapped[Optional[float]] = mapped_column(Float, default=0.0, nullable=True)
    
    # Structured statutory category verdicts: SATISFACTORY, DEFICIENT, NON_COMPLIANT
    faculty_verification_status: Mapped[str] = mapped_column(String(50), default="SATISFACTORY", nullable=False)
    land_building_status: Mapped[str] = mapped_column(String(50), default="SATISFACTORY", nullable=False)
    laboratories_equipment_status: Mapped[str] = mapped_column(String(50), default="SATISFACTORY", nullable=False)
    safety_and_amenities_status: Mapped[str] = mapped_column(String(50), default="SATISFACTORY", nullable=False)
    
    observations: Mapped[str] = mapped_column(Text, nullable=False)
    deficiencies_identified: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Structured checklist details and supporting evidence references
    checklist_data_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    evidence_references_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    location_evidence_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    virtual_attendance_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    
    # Scrutiny / RO Review: PENDING, ACCEPTED, RETURNED_FOR_CORRECTION
    review_status: Mapped[str] = mapped_column(String(50), default="PENDING", nullable=False, index=True)
    reviewed_by_user_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    reviewed_at: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    review_remarks: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    inspection: Mapped["EVCInspection"] = relationship("EVCInspection", back_populates="report_versions")
    submitted_by: Mapped["User"] = relationship("User", foreign_keys=[submitted_by_user_id])
    reviewed_by: Mapped[Optional["User"]] = relationship("User", foreign_keys=[reviewed_by_user_id])
