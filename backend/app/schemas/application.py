from typing import List, Optional, Any, Dict
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class ApplicationCreate(BaseModel):
    template_id: str
    academic_year: str = "2026-2027"
    submission_data: Dict[str, Any] = Field(default_factory=dict)


class ApplicationEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    actor_id: str
    event_type: str
    from_status: Optional[str]
    to_status: Optional[str]
    remarks: Optional[str]
    event_payload_json: Optional[str]
    created_at: datetime


class ApplicationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    application_number: str
    institution_id: str
    template_id: str
    version_id: str
    current_status: str
    academic_year: str
    submission_data_json: str
    submission_date: Optional[str]
    sla_deadline: Optional[str]
    applicant_user_id: str
    assigned_scrutiny_officer_id: Optional[str]
    assigned_regional_officer_id: Optional[str]
    delay_risk_score: Optional[float]
    delay_risk_factors_json: Optional[str]
    created_at: datetime
    updated_at: datetime
    events: List[ApplicationEventResponse] = []


class ApplicationTransitionRequest(BaseModel):
    target_status: str
    remarks: str
    checklist_verification: Optional[Dict[str, Any]] = None
