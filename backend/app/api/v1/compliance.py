from typing import List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Query, status, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.user import User
from app.security.dependencies import get_current_user, require_roles
from app.services.compliance_service import ComplianceService
from app.workers.compliance_worker import evaluate_compliance_deadlines_and_escalations
from app.schemas.compliance import (
    ObligationCreateRequest,
    ObligationUpdateRequest,
    ObligationStatusTransitionRequest,
    EvidenceSubmitRequest,
    OfficerReviewRequest,
    ComplianceObligationResponse,
    ComplianceSummaryReportResponse,
    InstitutionComplianceReportItem,
    ComplianceDeadlineItemResponse,
    ComplianceDeficiencyReportItem,
    ComplianceEscalationResponse,
)

router = APIRouter(prefix="/compliance", tags=["Post-Approval Compliance & Monitoring"])


# ==============================================================================
# OBLIGATIONS CRUD & LIFECYCLE (M14)
# ==============================================================================

@router.post(
    "/obligations",
    response_model=ComplianceObligationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new post-approval compliance obligation",
)
async def create_obligation(
    payload: ObligationCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles("SCRUTINY_OFFICER", "REGIONAL_OFFICER", "SUPER_ADMIN", "ADMIN")),
):
    """
    Creates a new post-approval compliance obligation.
    Restricted to authorized scrutiny officers, regional officers, and administrators.
    """
    service = ComplianceService(db)
    return await service.create_obligation(payload, current_user)


@router.get(
    "/obligations",
    response_model=List[ComplianceObligationResponse],
    summary="List compliance obligations with filtering and tenant isolation",
)
async def list_obligations(
    category: Optional[str] = Query(None, description="Category filter"),
    status: Optional[str] = Query(None, description="Status filter"),
    institution_id: Optional[str] = Query(None, description="Institution filter (officers/admins only)"),
    search: Optional[str] = Query(None, description="Search term for code, title, or reference"),
    overdue_only: bool = Query(False, description="Filter only overdue obligations"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Retrieves compliance obligations.
    Institutional users are strictly isolated to their own institution's obligations.
    """
    service = ComplianceService(db)
    items, _ = await service.list_obligations(
        current_user=current_user,
        category=category,
        status=status,
        institution_id=institution_id,
        search=search,
        overdue_only=overdue_only,
        limit=limit,
        offset=offset,
    )
    return items


@router.get(
    "/obligations/{obligation_id}",
    response_model=ComplianceObligationResponse,
    summary="Get detailed view of a single compliance obligation",
)
async def get_obligation(
    obligation_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Retrieves full details of an obligation including evidence attachments and review history.
    """
    service = ComplianceService(db)
    return await service.get_obligation(obligation_id, current_user)


@router.put(
    "/obligations/{obligation_id}",
    response_model=ComplianceObligationResponse,
    summary="Update configurable obligation attributes",
)
async def update_obligation(
    obligation_id: str,
    payload: ObligationUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles("SCRUTINY_OFFICER", "REGIONAL_OFFICER", "SUPER_ADMIN", "ADMIN")),
):
    """
    Updates obligation details. Only open obligations can be edited.
    """
    service = ComplianceService(db)
    return await service.update_obligation(obligation_id, payload, current_user)


@router.post(
    "/obligations/{obligation_id}/evidence",
    response_model=ComplianceObligationResponse,
    summary="Submit supporting evidence for an obligation",
)
async def submit_evidence(
    obligation_id: str,
    payload: EvidenceSubmitRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Uploads supporting evidence and transitions obligation status to SUBMITTED.
    Institution users may only submit evidence for their own institution.
    """
    service = ComplianceService(db)
    return await service.submit_evidence(obligation_id, payload, current_user)


@router.post(
    "/obligations/{obligation_id}/review",
    response_model=ComplianceObligationResponse,
    summary="Officer review determination for submitted obligation",
)
async def officer_review(
    obligation_id: str,
    payload: OfficerReviewRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles("SCRUTINY_OFFICER", "REGIONAL_OFFICER", "SUPER_ADMIN", "ADMIN")),
):
    """
    Officer review determination:
    - VERIFIED_COMPLIANT -> Transitions status to COMPLIANT
    - DEFICIENCY_FLAGGED -> Transitions status to DEFICIENT (with optional cure deadline extension)
    - CLOSED -> Closes obligation
    Emits an in-app institutional notification and chained SHA-256 audit log.
    """
    service = ComplianceService(db)
    return await service.officer_review(obligation_id, payload, current_user)


@router.post(
    "/obligations/{obligation_id}/transition",
    response_model=ComplianceObligationResponse,
    summary="Trigger validated lifecycle state transition",
)
async def transition_status(
    obligation_id: str,
    payload: ObligationStatusTransitionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Transitions obligation state using validated state machine rules.
    Invalid transitions are blocked with HTTP 400.
    """
    service = ComplianceService(db)
    return await service.transition_status(
        obligation_id=obligation_id,
        target_status=payload.target_status,
        comments=payload.comments,
        actor=current_user,
    )


# ==============================================================================
# COMPLIANCE REPORTS & CSV EXPORT (M16)
# ==============================================================================

@router.get(
    "/reports/summary",
    response_model=ComplianceSummaryReportResponse,
    summary="Summary KPI metrics across compliance obligations",
)
async def get_compliance_summary(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Returns high-level compliance KPIs, category breakdown, and escalation counts.
    """
    service = ComplianceService(db)
    return await service.get_summary_report(current_user)


@router.get(
    "/reports/by-institution",
    response_model=List[InstitutionComplianceReportItem],
    summary="Compliance status aggregated by institution",
)
async def get_institution_reports(
    region: Optional[str] = Query(None, description="Filter by region (officers/admins only)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Returns institution compliance ratings and performance breakdown.
    """
    service = ComplianceService(db)
    return await service.get_institution_reports(current_user, region=region)


@router.get(
    "/reports/deadlines",
    response_model=List[ComplianceDeadlineItemResponse],
    summary="Upcoming deadlines, expirations, and calendar items",
)
async def get_deadlines_report(
    days_ahead: int = Query(60, ge=1, le=365, description="Lookahead window in days"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Calendar and deadline tracking report. Categorizes items into urgency buckets:
    OVERDUE, DUE_TODAY, CRITICAL_7_DAYS, APPROACHING_30_DAYS, HEALTHY.
    """
    service = ComplianceService(db)
    return await service.get_deadlines_report(current_user, days_ahead=days_ahead)


@router.get(
    "/reports/deficiencies",
    response_model=List[ComplianceDeficiencyReportItem],
    summary="Review queue of outstanding deficiencies and overdue obligations",
)
async def get_deficiencies_report(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Lists all obligations flagged with deficiencies or overdue for officer review.
    """
    service = ComplianceService(db)
    return await service.get_deficiencies_report(current_user)


@router.get(
    "/reports/export-csv",
    summary="Export compliance records as CSV with formula injection protection",
)
async def export_compliance_csv(
    category: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    institution_id: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Generates a downloadable CSV export of compliance records.
    OWASP Sanitization: Protects against spreadsheet formula injection by sanitizing leading special characters.
    """
    service = ComplianceService(db)
    csv_content = await service.export_compliance_csv(
        current_user=current_user,
        category=category,
        status=status,
        institution_id=institution_id,
    )

    filename = f"aicte_compliance_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-cache",
        },
    )


# ==============================================================================
# ESCALATIONS & WORKER TRIGGER (M15)
# ==============================================================================

@router.get(
    "/escalations",
    response_model=List[ComplianceEscalationResponse],
    summary="List compliance escalation events and notifications",
)
async def list_escalations(
    unresolved_only: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Returns recorded Level 1 and Level 2 escalations.
    """
    from sqlalchemy import select
    from app.models.compliance import ComplianceEscalation

    user_roles = [r.code for r in current_user.roles]
    stmt = select(ComplianceEscalation).order_by(ComplianceEscalation.created_at.desc())

    if "INSTITUTION_USER" in user_roles or "INSTITUTION_ADMIN" in user_roles:
        stmt = stmt.where(ComplianceEscalation.institution_id == current_user.institution_id)
    if unresolved_only:
        stmt = stmt.where(ComplianceEscalation.is_resolved == False)

    res = await db.execute(stmt)
    escalations = res.scalars().all()
    return [
        ComplianceEscalationResponse(
            id=e.id,
            obligation_id=e.obligation_id,
            institution_id=e.institution_id,
            escalation_level=e.escalation_level,
            severity=e.severity,
            trigger_reason=e.trigger_reason,
            days_overdue=e.days_overdue,
            notified_roles_json=e.notified_roles_json,
            notification_id=e.notification_id,
            is_resolved=e.is_resolved,
            resolved_at=e.resolved_at,
            resolved_by_user_id=e.resolved_by_user_id,
            resolution_notes=e.resolution_notes,
            created_at=e.created_at,
        )
        for e in escalations
    ]


@router.post(
    "/monitoring/trigger",
    summary="Trigger on-demand compliance monitoring and deadline evaluation",
)
async def trigger_monitoring_worker(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles("SUPER_ADMIN", "ADMIN")),
):
    """
    Manually triggers the compliance deadline monitoring and escalation worker cycle.
    Restricted to Administrators.
    """
    actions = await evaluate_compliance_deadlines_and_escalations(db)
    return {
        "status": "success",
        "actions_evaluated": actions,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "message": f"Compliance monitoring evaluation cycle executed successfully. Actions triggered: {actions}.",
    }
