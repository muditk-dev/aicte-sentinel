import json
from typing import List
from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.core.exceptions import NotFoundError, PermissionDeniedError
from app.models.application import Application, ApplicationEvent
from app.models.document import Document, ScrutinyFinding
from app.models.user import User
from app.schemas.document import ScrutinyFindingCreate, ScrutinyFindingResponse
from app.security.dependencies import get_current_user, require_roles
from app.audit.service import record_audit_event

router = APIRouter(tags=["Document Scrutiny"])


@router.get("/applications/{application_id}/scrutiny", response_model=List[ScrutinyFindingResponse])
async def list_scrutiny_findings(
    application_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve all recorded scrutiny findings for an application docket."""
    stmt = select(Application).where(Application.id == application_id)
    app = (await db.execute(stmt)).scalar_one_or_none()
    if not app:
        raise NotFoundError("Application", application_id)

    user_roles = [r.code for r in current_user.roles]
    if "INSTITUTION_ADMIN" in user_roles and "SUPER_ADMIN" not in user_roles:
        if app.institution_id != current_user.institution_id:
            raise PermissionDeniedError("Cannot inspect scrutiny findings for another institution.")

    findings_stmt = (
        select(ScrutinyFinding)
        .where(ScrutinyFinding.application_id == application_id)
        .order_by(ScrutinyFinding.created_at.desc())
    )
    result = await db.execute(findings_stmt)
    return result.scalars().all()


@router.post(
    "/applications/{application_id}/scrutiny",
    response_model=ScrutinyFindingResponse,
    status_code=status.HTTP_201_CREATED,
)
async def record_scrutiny_finding(
    application_id: str,
    payload: ScrutinyFindingCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles("SCRUTINY_OFFICER", "REGIONAL_OFFICER", "SUPER_ADMIN")),
):
    """
    Records an official scrutiny finding by an authorized regulatory officer.
    - Updates document verification state.
    - AI advisory outputs cannot perform this operation automatically.
    - Immutable audit and application event records are emitted.
    """
    stmt = select(Application).where(Application.id == application_id)
    app = (await db.execute(stmt)).scalar_one_or_none()
    if not app:
        raise NotFoundError("Application", application_id)

    # If linked to a document, verify document belongs to this application
    if payload.document_id:
        doc_stmt = select(Document).where(Document.id == payload.document_id, Document.application_id == application_id)
        doc = (await db.execute(doc_stmt)).scalar_one_or_none()
        if not doc:
            raise NotFoundError("Document for Application", payload.document_id)
        # Synchronize document verification status
        doc.verification_status = payload.finding_status

    finding = ScrutinyFinding(
        application_id=application_id,
        document_id=payload.document_id,
        category=payload.category,
        officer_id=current_user.id,
        finding_status=payload.finding_status,
        reason=payload.reason,
        notes=payload.notes,
        is_advisory_ai=False,
    )
    db.add(finding)
    await db.flush()

    # Application timeline event
    app_event = ApplicationEvent(
        application_id=application_id,
        actor_id=current_user.id,
        event_type="SCRUTINY_FINDING_RECORDED",
        remarks=f"Scrutiny for '{payload.category}': {payload.finding_status} — {payload.reason}",
        event_payload_json=json.dumps({
            "category": payload.category,
            "status": payload.finding_status,
            "reason": payload.reason,
        }),
    )
    db.add(app_event)

    # Chained audit event
    await record_audit_event(
        db=db,
        actor_id=current_user.id,
        action="RECORD_SCRUTINY_FINDING",
        resource_type="ScrutinyFinding",
        resource_id=finding.id,
        details={
            "application_id": application_id,
            "category": payload.category,
            "finding_status": payload.finding_status,
            "reason": payload.reason,
        },
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("User-Agent"),
    )

    await db.commit()
    await db.refresh(finding)
    return finding
