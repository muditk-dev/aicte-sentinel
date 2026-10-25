from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class DecisionConditionCreate(BaseModel):
    condition_code: str = Field(..., max_length=50)
    description: str = Field(..., min_length=5)
    due_date: str = Field(..., max_length=50)


class DecisionConditionResponse(BaseModel):
    id: str
    decision_id: str
    condition_code: str
    description: str
    due_date: str
    compliance_status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class StatutoryDecisionIssueRequest(BaseModel):
    application_id: str
    decision_type: str = Field(..., description="APPROVED, CONDITIONALLY_APPROVED, REJECTED, RETURNED_FOR_REVIEW")
    reasons: str = Field(..., min_length=15, description="Statutory justification and findings")
    evidence_references: List[str] = Field(default_factory=list, description="Referenced EVC reports, Scrutiny items, Hearing minutes")
    intake_approved: Optional[int] = Field(None, ge=0, le=10000)
    valid_for_years: int = Field(1, ge=1, le=5)
    governing_policy_version: str = Field("AICTE-APH-2026-V1", max_length=50)
    conditions: List[DecisionConditionCreate] = Field(default_factory=list, description="Mandatory for CONDITIONALLY_APPROVED")
    declaration_attestation: str = Field(
        ...,
        min_length=20,
        description="Formal statutory declaration text affirming human officer attestation without unverified automated action",
    )


class StatutoryDecisionResponse(BaseModel):
    id: str
    application_id: str
    application_number: Optional[str] = None
    institution_id: str
    institution_name: Optional[str] = None
    decision_number: str
    decision_type: str
    academic_year: str
    authority_role: str
    authorized_by_user_id: str
    authorized_by_name: Optional[str] = None
    authorized_at: str
    governing_policy_version: str
    reasons: str
    evidence_references: List[str] = Field(default_factory=list)
    intake_approved: Optional[int] = None
    valid_for_years: int
    is_final: bool
    is_reconsidered: bool
    reconsideration_reference: Optional[str] = None
    sha256_attestation: str
    declaration_text: str
    conditions: List[DecisionConditionResponse] = Field(default_factory=list)
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ReconsiderationRequest(BaseModel):
    appeal_reason: str = Field(..., min_length=20)
    appeal_petition_reference: str = Field(..., max_length=100)
