from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict, EmailStr


class ExpertBase(BaseModel):
    name: str = Field(..., max_length=150)
    email: EmailStr
    phone: Optional[str] = Field(None, max_length=50)
    designation: str = Field(..., max_length=150)
    organization: str = Field(..., max_length=255)
    expert_type: str = Field("ACADEMIC", description="ACADEMIC, INDUSTRY, REGULATORY")
    qualifications: str = Field(..., max_length=255)
    experience_years: int = Field(10, ge=1, le=60)
    specializations: List[str] = Field(default_factory=list)
    affiliated_institution_ids: List[str] = Field(default_factory=list)
    alma_mater: str = Field(..., max_length=255)
    state: str = Field(..., max_length=100)
    district: str = Field(..., max_length=100)
    availability_status: str = Field("AVAILABLE", description="AVAILABLE, BUSY, UNAVAILABLE")
    conflict_declarations: List[str] = Field(default_factory=list)


class ExpertCreate(ExpertBase):
    user_id: Optional[str] = None


class ExpertResponse(ExpertBase):
    id: str
    user_id: Optional[str] = None
    is_active: bool
    verification_status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ConflictCheckRequest(BaseModel):
    expert_id: str
    application_id: str


class ConflictCheckResponse(BaseModel):
    expert_id: str
    expert_name: str
    application_id: str
    institution_id: str
    institution_name: str
    has_conflict: bool
    is_blocked: bool
    policy_version: str
    conflict_reasons: List[str]


class EVCInspectionCreate(BaseModel):
    application_id: str
    inspection_mode: str = Field("PHYSICAL", description="PHYSICAL, VIRTUAL, HYBRID")
    scheduled_start_date: str
    scheduled_end_date: str
    chairperson_id: Optional[str] = None
    meeting_link: Optional[str] = None
    location_coordinates: Optional[str] = None
    location_address: Optional[str] = None


class EVCExpertAssignRequest(BaseModel):
    expert_id: str
    role: str = Field("MEMBER", description="CHAIRPERSON, MEMBER, CONVENER, SPECIALIST")
    override_conflict: bool = False
    override_justification: Optional[str] = None


class EVCPanelMemberResponse(BaseModel):
    id: str
    inspection_id: str
    expert_id: str
    expert_name: str
    expert_designation: str
    expert_organization: str
    role: str
    conflict_check_passed: bool
    conflict_notes: Optional[str] = None
    attendance_status: str
    attendance_timestamp: Optional[str] = None
    sign_off_status: str
    sign_off_timestamp: Optional[str] = None
    sign_off_remarks: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class EVCReportSubmit(BaseModel):
    overall_recommendation: str = Field(..., description="RECOMMENDED, DEFICIENT, SERIOUS_VIOLATIONS")
    infrastructure_score: Optional[float] = Field(0.0, ge=0.0, le=100.0)
    faculty_verification_status: str = Field("SATISFACTORY", description="SATISFACTORY, DEFICIENT, NON_COMPLIANT")
    land_building_status: str = Field("SATISFACTORY", description="SATISFACTORY, DEFICIENT, NON_COMPLIANT")
    laboratories_equipment_status: str = Field("SATISFACTORY", description="SATISFACTORY, DEFICIENT, NON_COMPLIANT")
    safety_and_amenities_status: str = Field("SATISFACTORY", description="SATISFACTORY, DEFICIENT, NON_COMPLIANT")
    observations: str = Field(..., min_length=10)
    deficiencies_identified: Optional[str] = None
    checklist_data: Dict[str, Any] = Field(default_factory=dict)
    evidence_references: List[str] = Field(default_factory=list)
    location_evidence: Dict[str, Any] = Field(default_factory=dict)
    virtual_attendance: Dict[str, Any] = Field(default_factory=dict)


class EVCReportReviewRequest(BaseModel):
    review_status: str = Field(..., description="ACCEPTED or RETURNED_FOR_CORRECTION")
    review_remarks: str = Field(..., min_length=5)


class EVCReportVersionResponse(BaseModel):
    id: str
    inspection_id: str
    version_number: int
    application_id: str
    submitted_by_user_id: str
    submitted_by_name: Optional[str] = None
    submitted_at: str
    sha256_hash: str
    overall_recommendation: str
    infrastructure_score: Optional[float] = None
    faculty_verification_status: str
    land_building_status: str
    laboratories_equipment_status: str
    safety_and_amenities_status: str
    observations: str
    deficiencies_identified: Optional[str] = None
    checklist_data: Dict[str, Any] = Field(default_factory=dict)
    evidence_references: List[str] = Field(default_factory=list)
    location_evidence: Dict[str, Any] = Field(default_factory=dict)
    virtual_attendance: Dict[str, Any] = Field(default_factory=dict)
    review_status: str
    reviewed_by_user_id: Optional[str] = None
    reviewed_by_name: Optional[str] = None
    reviewed_at: Optional[str] = None
    review_remarks: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class EVCInspectionResponse(BaseModel):
    id: str
    application_id: str
    institution_id: str
    institution_name: Optional[str] = None
    inspection_number: str
    inspection_mode: str
    status: str
    scheduled_start_date: str
    scheduled_end_date: str
    actual_inspection_date: Optional[str] = None
    chairperson_id: Optional[str] = None
    chairperson_name: Optional[str] = None
    meeting_link: Optional[str] = None
    location_coordinates: Optional[str] = None
    location_address: Optional[str] = None
    cancellation_reason: Optional[str] = None
    assigned_by_user_id: str
    panel_members: List[EVCPanelMemberResponse] = Field(default_factory=list)
    latest_report: Optional[EVCReportVersionResponse] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class InspectionTransitionRequest(BaseModel):
    target_status: str = Field(..., description="SCHEDULED, IN_PROGRESS, REPORT_SUBMITTED, UNDER_REVIEW, ACCEPTED, RETURNED_FOR_CORRECTION")
    remarks: Optional[str] = None
