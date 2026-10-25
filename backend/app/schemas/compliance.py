from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


# ==============================================================================
# EVIDENCE SCHEMAS
# ==============================================================================

class EvidenceSubmitRequest(BaseModel):
    title: str = Field(..., min_length=3, max_length=200)
    description: Optional[str] = None
    document_id: Optional[str] = None
    file_url: Optional[str] = None
    sha256_hash: Optional[str] = None
    submission_notes: Optional[str] = None


class ObligationEvidenceResponse(BaseModel):
    id: str
    obligation_id: str
    document_id: Optional[str] = None
    title: str
    description: Optional[str] = None
    file_url: Optional[str] = None
    sha256_hash: Optional[str] = None
    uploaded_by_user_id: str
    submission_notes: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ==============================================================================
# HISTORY SCHEMAS
# ==============================================================================

class ObligationReviewHistoryResponse(BaseModel):
    id: str
    obligation_id: str
    actor_id: str
    actor_role: str
    action: str
    previous_status: str
    new_status: str
    comments: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ==============================================================================
# ESCALATION SCHEMAS
# ==============================================================================

class ComplianceEscalationResponse(BaseModel):
    id: str
    obligation_id: str
    institution_id: str
    escalation_level: int
    severity: str
    trigger_reason: str
    days_overdue: int
    notified_roles_json: str
    notification_id: Optional[str] = None
    is_resolved: bool
    resolved_at: Optional[datetime] = None
    resolved_by_user_id: Optional[str] = None
    resolution_notes: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ==============================================================================
# OBLIGATION REQUEST / RESPONSE SCHEMAS
# ==============================================================================

class ObligationCreateRequest(BaseModel):
    institution_id: str
    application_id: Optional[str] = None
    decision_id: Optional[str] = None
    title: str = Field(..., min_length=3, max_length=255)
    description: str = Field(..., min_length=5)
    category: str = Field(..., description="FACULTY_RATIO, SAFETY_CLEARANCE, INFRASTRUCTURE, AFFILIATION, FINANCIAL_DISCLOSURE, ANNUAL_REPORT, GENERAL")
    source_reference: str = Field(..., description="Statutory reference, e.g. APH 2026-27 Clause 4.1.1")
    applicability: str = "ALL_TECHNICAL_INSTITUTIONS"
    assigned_officer_id: Optional[str] = None
    issue_date: datetime
    due_date: datetime
    recurrence: str = "ONE_TIME"  # ONE_TIME, ANNUAL, BIENNIAL, QUARTERLY
    is_synthetic_demonstration: bool = False


class ObligationUpdateRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    source_reference: Optional[str] = None
    applicability: Optional[str] = None
    assigned_officer_id: Optional[str] = None
    due_date: Optional[datetime] = None
    recurrence: Optional[str] = None


class ObligationStatusTransitionRequest(BaseModel):
    target_status: str = Field(..., description="Target status: SUBMITTED, UNDER_REVIEW, COMPLIANT, DEFICIENT, OVERDUE, CLOSED")
    comments: Optional[str] = None


class OfficerReviewRequest(BaseModel):
    decision: str = Field(..., description="VERIFIED_COMPLIANT, DEFICIENCY_FLAGGED, or CLOSED")
    review_comments: str = Field(..., min_length=3)
    deficiency_cure_days: Optional[int] = Field(None, description="Optional extension days if DEFICIENCY_FLAGGED")


class ComplianceObligationResponse(BaseModel):
    id: str
    obligation_code: str
    institution_id: str
    institution_name: Optional[str] = None
    application_id: Optional[str] = None
    decision_id: Optional[str] = None
    title: str
    description: str
    category: str
    source_reference: str
    applicability: str
    assigned_officer_id: Optional[str] = None
    assigned_officer_name: Optional[str] = None
    issue_date: datetime
    due_date: datetime
    recurrence: str
    status: str
    is_synthetic_demonstration: bool
    is_automated_advisory: bool
    closed_at: Optional[datetime] = None
    closed_by_user_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    evidences: List[ObligationEvidenceResponse] = []
    history: List[ObligationReviewHistoryResponse] = []

    class Config:
        from_attributes = True


# ==============================================================================
# REPORT SCHEMAS
# ==============================================================================

class CategoryBreakdownItem(BaseModel):
    category: str
    total: int
    compliant: int
    pending: int
    deficient: int
    overdue: int


class ComplianceSummaryReportResponse(BaseModel):
    total_obligations: int
    total_compliant: int
    total_pending: int
    total_under_review: int
    total_deficient: int
    total_overdue: int
    total_closed: int
    compliance_rate_percent: float
    categories_breakdown: List[CategoryBreakdownItem]
    active_escalations_count: int
    is_synthetic_demonstration: bool = True


class InstitutionComplianceReportItem(BaseModel):
    institution_id: str
    institution_name: str
    institution_code: str
    region: str
    state: str
    total_obligations: int
    compliant_count: int
    pending_count: int
    overdue_count: int
    deficient_count: int
    compliance_percentage: float
    is_fully_compliant: bool


class ComplianceDeadlineItemResponse(BaseModel):
    id: str
    item_type: str  # OBLIGATION, CERTIFICATE_EXPIRY, APPROVAL_EXPIRY
    title: str
    institution_id: str
    institution_name: str
    due_date: datetime
    days_remaining: int
    urgency_status: str  # OVERDUE, DUE_TODAY, CRITICAL_7_DAYS, APPROACHING_30_DAYS, HEALTHY
    category: str
    reference_code: str


class ComplianceDeficiencyReportItem(BaseModel):
    obligation_id: str
    obligation_code: str
    title: str
    institution_id: str
    institution_name: str
    category: str
    source_reference: str
    due_date: datetime
    days_overdue: int
    last_review_comments: Optional[str] = None
    assigned_officer_name: Optional[str] = None
