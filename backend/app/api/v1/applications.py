import json
import uuid
from typing import List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.core.database import get_db
from app.core.exceptions import NotFoundError, PermissionDeniedError
from app.models.application import Application, ApplicationEvent
from app.models.workflow import WorkflowVersion
from app.models.user import User
from app.schemas.application import (
    ApplicationCreate,
    ApplicationResponse,
    ApplicationTransitionRequest,
)
from app.security.dependencies import get_current_user
from app.workflows.engine import WorkflowEngine
from app.audit.service import record_audit_event

router = APIRouter(prefix="/applications", tags=["Applications Lifecycle"])


@router.get("", response_model=List[ApplicationResponse])
async def list_applications(
    status_filter: Optional[str] = Query(None, alias="status"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List applications with strict tenant isolation and role boundaries."""
    stmt = select(Application).options(selectinload(Application.events))
    user_roles = [r.code for r in current_user.roles]

    # Tenant enforcement: Institutions can ONLY see their own applications
    if "INSTITUTION_ADMIN" in user_roles and "SUPER_ADMIN" not in user_roles:
        stmt = stmt.where(Application.institution_id == current_user.institution_id)
    elif "REGIONAL_OFFICER" in user_roles and "SUPER_ADMIN" not in user_roles and current_user.assigned_region:
        from app.models.institution import Institution
        stmt = stmt.join(Institution).where(Institution.region == current_user.assigned_region)

    if status_filter:
        stmt = stmt.where(Application.current_status == status_filter)

    stmt = stmt.order_by(Application.created_at.desc())
    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("", response_model=ApplicationResponse, status_code=status.HTTP_201_CREATED)
async def create_application(
    payload: ApplicationCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Initiate a statutory application for the authenticated institution."""
    if not current_user.institution_id:
        raise PermissionDeniedError("Only institution authorized representatives can submit intake applications.")

    # Fetch active version for the selected template
    v_stmt = (
        select(WorkflowVersion)
        .where(WorkflowVersion.template_id == payload.template_id, WorkflowVersion.is_published.is_(True))
        .order_by(WorkflowVersion.version_number.desc())
        .limit(1)
    )
    v_res = await db.execute(v_stmt)
    version = v_res.scalar_one_or_none()
    if not version:
        raise NotFoundError("Active WorkflowVersion for Template", payload.template_id)

    app_num = f"AICTE-{datetime.now(timezone.utc).year}-{uuid.uuid4().hex[:6].upper()}"

    app = Application(
        application_number=app_num,
        institution_id=current_user.institution_id,
        template_id=payload.template_id,
        version_id=version.id,
        current_status="DRAFT",
        academic_year=payload.academic_year,
        submission_data_json=json.dumps(payload.submission_data),
        applicant_user_id=current_user.id,
        delay_risk_score=0.15,
        delay_risk_factors_json=json.dumps([
            {"factor": "Intake draft created", "impact": "LOW", "detail": "Initial submission pending review"}
        ]),
    )
    db.add(app)
    await db.flush()

    # Initial event
    event = ApplicationEvent(
        application_id=app.id,
        actor_id=current_user.id,
        event_type="APPLICATION_INITIALIZED",
        to_status="DRAFT",
        remarks="Application draft created by institution representative.",
    )
    db.add(event)

    await record_audit_event(
        db=db,
        actor_id=current_user.id,
        action="CREATE_APPLICATION_DRAFT",
        resource_type="Application",
        resource_id=app.id,
        details={"application_number": app_num},
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("User-Agent"),
    )

    await db.commit()
    await db.refresh(app)
    # Reload with events
    stmt = select(Application).options(selectinload(Application.events)).where(Application.id == app.id)
    reloaded = (await db.execute(stmt)).scalar_one()
    return reloaded


@router.get("/{application_id}", response_model=ApplicationResponse)
async def get_application(
    application_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Fetch application details along with full statutory timeline."""
    stmt = (
        select(Application)
        .options(selectinload(Application.events))
        .where(Application.id == application_id)
    )
    result = await db.execute(stmt)
    app = result.scalar_one_or_none()

    if not app:
        raise NotFoundError("Application", application_id)

    # Tenant check
    user_roles = [r.code for r in current_user.roles]
    if "INSTITUTION_ADMIN" in user_roles and "SUPER_ADMIN" not in user_roles:
        if app.institution_id != current_user.institution_id:
            raise PermissionDeniedError("Access to this application is restricted under institutional tenant boundary.")

    return app


@router.post("/{application_id}/transition", response_model=ApplicationResponse)
async def transition_application_state(
    application_id: str,
    payload: ApplicationTransitionRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Execute a statutory state transition guarded by the state machine and role checks."""
    app = await WorkflowEngine.transition(
        db=db,
        application_id=application_id,
        target_status=payload.target_status,
        actor=current_user,
        remarks=payload.remarks,
        metadata=payload.checklist_verification,
        ip_address=request.client.host if request.client else None,
    )
    stmt = select(Application).options(selectinload(Application.events)).where(Application.id == app.id)
    reloaded = (await db.execute(stmt)).scalar_one()
    return reloaded
