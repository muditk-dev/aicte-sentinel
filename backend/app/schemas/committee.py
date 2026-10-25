from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class CommitteeBase(BaseModel):
    code: str = Field(..., max_length=50)
    name: str = Field(..., max_length=150)
    committee_type: str = Field("SHC", description="SHC (Standing Hearing Committee), SAC (Standing Appellate Committee)")
    description: Optional[str] = Field(None, max_length=255)
    quorum_required: int = Field(3, ge=1, le=15)
    valid_from: str
    valid_to: Optional[str] = None


class CommitteeCreate(CommitteeBase):
    pass


class CommitteeMemberCreate(BaseModel):
    user_id: Optional[str] = None
    expert_id: Optional[str] = None
    member_name: str = Field(..., max_length=150)
    member_role: str = Field("MEMBER", description="CHAIRPERSON, MEMBER_SECRETARY, LEGAL_EXPERT, ACADEMIC_EXPERT, MEMBER")
    conflict_declarations: List[str] = Field(default_factory=list)


class CommitteeMembershipResponse(BaseModel):
    id: str
    committee_id: str
    user_id: Optional[str] = None
    expert_id: Optional[str] = None
    member_name: str
    member_role: str
    conflict_declarations: List[str] = Field(default_factory=list)
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CommitteeResponse(CommitteeBase):
    id: str
    is_active: bool
    memberships: List[CommitteeMembershipResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class HearingDocketCreate(BaseModel):
    application_id: str
    matter_summary: str = Field(..., min_length=10)
    referred_by: str = Field("REGIONAL_OFFICE", max_length=100)
    institutional_representative_name: Optional[str] = None


class HearingDocketResponse(BaseModel):
    id: str
    hearing_id: str
    application_id: str
    institution_id: str
    institution_name: Optional[str] = None
    application_number: Optional[str] = None
    docket_number: str
    matter_summary: str
    referred_by: str
    institutional_representative_name: Optional[str] = None
    docket_status: str
    docket_recommendation: Optional[str] = None
    docket_remarks: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class HearingAttendanceRecord(BaseModel):
    member_name: str
    member_role: str
    user_id: Optional[str] = None
    attended: bool
    attendance_mode: str = Field("IN_PERSON", description="IN_PERSON or REMOTE")
    conflict_declared_for_docket_ids: Optional[str] = None


class HearingAttendanceResponse(BaseModel):
    id: str
    hearing_id: str
    member_name: str
    member_role: str
    user_id: Optional[str] = None
    attended: bool
    attendance_mode: str
    conflict_declared_for_docket_ids: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class HearingScheduleRequest(BaseModel):
    committee_id: str
    hearing_type: str = Field("SHC", description="SHC or SAC")
    scheduled_date: str
    meeting_mode: str = Field("HYBRID", description="PHYSICAL, VIRTUAL, HYBRID")
    venue_or_link: str = Field(..., max_length=500)
    agenda: str = Field(..., min_length=10)
    chairperson_name: Optional[str] = None


class HearingTransitionRequest(BaseModel):
    target_status: str = Field(..., description="NOTICE_ISSUED, IN_SESSION, MINUTES_PENDING, RECOMMENDATION_RECORDED, COMPLETED, POSTPONED, CANCELLED")
    reason: Optional[str] = None


class HearingMinutesRequest(BaseModel):
    minutes_of_meeting: str = Field(..., min_length=20)
    final_recommendation: str = Field(..., description="RECOMMEND_APPROVAL, RECOMMEND_REJECTION, RECOMMEND_RE_EVC, DISMISSED")
    recommendation_summary: str = Field(..., min_length=10)
    docket_outcomes: Optional[List[dict]] = None


class HearingResponse(BaseModel):
    id: str
    committee_id: str
    committee_name: Optional[str] = None
    hearing_number: str
    hearing_type: str
    status: str
    scheduled_date: str
    meeting_mode: str
    venue_or_link: str
    agenda: str
    postponement_reason: Optional[str] = None
    cancellation_reason: Optional[str] = None
    chairperson_name: Optional[str] = None
    conducted_at: Optional[str] = None
    minutes_of_meeting: Optional[str] = None
    final_recommendation: Optional[str] = None
    recommendation_summary: Optional[str] = None
    dockets: List[HearingDocketResponse] = Field(default_factory=list)
    attendances: List[HearingAttendanceResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
