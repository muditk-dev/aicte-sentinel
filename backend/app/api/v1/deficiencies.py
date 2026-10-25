import json
import uuid
from typing import List, Optional
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.config import settings
from app.core.exceptions import NotFoundError, PermissionDeniedError, ConflictError
from app.models.application import Application, ApplicationEvent
from app.models.deficiency import DeficiencyNotice, DeficiencyItem, DeficiencyResponse, Notification
from app.models.user import User
from app.schemas.deficiency import (
    DeficiencyNoticeCreate,
    DeficiencyNoticeResponse,
    DeficiencyResponseSubmit,
    DeficiencyNoticeReview,
)
from app.security.dependencies import get_current_user, require_roles
from app.workflows.engine import WorkflowEngine
from app.audit.service import record_audit_event

router = APIRouter(tags=["Deficiency Notices & Institutional Clarification"])


@router.get("/applications/{application_id}/deficiencies", response_model=List[DeficiencyNoticeResponse])
async def list_deficiency_notices(
    application_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve all deficiency notices issued for an application docket."""
    stmt = select(Application).where(Application.id == application_id)
    app = (await db.execute(stmt)).scalar_one_or_none()
    if not app:
        raise NotFoundError("Application", application_id)

    user_roles = [r.code for r in current_user.roles]
    if "INSTITUTION_ADMIN" in user_roles and "SUPER_ADMIN" not in user_roles:
        if app.institution_id != current_user.institution_id:
            raise PermissionDeniedError("Tenant violation: Access to deficiency notices for other institutions is restricted.")

    notices_stmt = (
        select(DeficiencyNotice)
        .options(selectinload(DeficiencyNotice.items), selectinload(DeficiencyNotice.responses))
        .where(DeficiencyNotice.application_id == application_id)
        .order_by(DeficiencyNotice.created_at.desc())
    )
    result = await db.execute(notices_stmt)
    return result.scalars().all()


@router.post(
    "/applications/{application_id}/deficiencies",
    response_model=DeficiencyNoticeResponse,
    status_code=status.HTTP_201_CREATED,
)
async def draft_and_issue_deficiency_notice(
    application_id: str,
    payload: DeficiencyNoticeCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles("SCRUTINY_OFFICER", "REGIONAL_OFFICER", "SUPER_ADMIN")),
):
    """
    Drafts and formally issues a statutory deficiency notice with a mandatory cure window.
    - Creates notice and individual deficiency items.
    - Transitions application to DEFICIENCY_ISSUED if in UNDER_SCRUTINY.
    - Emits in-app institutional notification and cryptographic audit records.
    """
    stmt = select(Application).where(Application.id == application_id)
    app = (await db.execute(stmt)).scalar_one_or_none()
    if not app:
        raise NotFoundError("Application", application_id)

    cure_days = payload.cure_days or settings.DEFICIENCY_DEFAULT_CURE_DAYS
    now = datetime.now(timezone.utc)
    due_date = now + timedelta(days=cure_days)

    notice_num = f"DEF-{now.year}-{uuid.uuid4().hex[:6].upper()}"

    notice = DeficiencyNotice(
        notice_number=notice_num,
        application_id=application_id,
        institution_id=app.institution_id,
        issuing_officer_id=current_user.id,
        status="ISSUED",
        due_date=due_date,
        officer_remarks=payload.officer_remarks,
        issued_at=now,
    )
    db.add(notice)
    await db.flush()

    for item_data in payload.items:
        item = DeficiencyItem(
            notice_id=notice.id,
            document_id=item_data.document_id,
            requirement_title=item_data.requirement_title,
            description=item_data.description,
            required_corrective_action=item_data.required_corrective_action,
            item_status="PENDING",
        )
        db.add(item)

    # If application is UNDER_SCRUTINY, transition to DEFICIENCY_ISSUED
    if app.current_status == "UNDER_SCRUTINY":
        try:
            await WorkflowEngine.transition(
                db=db,
                application_id=app.id,
                target_status="DEFICIENCY_ISSUED",
                actor=current_user,
                remarks=f"Formal deficiency notice {notice_num} issued with {cure_days}-day cure period.",
                metadata={"notice_id": notice.id, "notice_number": notice_num},
                ip_address=request.client.host if request.client else None,
            )
        except Exception:
            # Fallback direct state set if already in transition
            app.current_status = "DEFICIENCY_ISSUED"

    # In-app notification for the institution
    notif = Notification(
        institution_id=app.institution_id,
        title=f"Statutory Deficiency Notice Issued: {notice_num}",
        message=f"Deficiencies flagged in application {app.application_number}. Mandatory cure window expires on {due_date.strftime('%d-%b-%Y %H:%M UTC')}.",
        category="DEFICIENCY_ISSUED",
        link_url=f"/applications/{app.id}",
        is_read=False,
        dedup_key=f"notice_issued_{notice.id}",
    )
    db.add(notif)

    # Cryptographic Audit Log
    await record_audit_event(
        db=db,
        actor_id=current_user.id,
        action="ISSUE_DEFICIENCY_NOTICE",
        resource_type="DeficiencyNotice",
        resource_id=notice.id,
        details={
            "notice_number": notice_num,
            "application_id": application_id,
            "due_date": due_date.isoformat(),
            "items_count": len(payload.items),
        },
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("User-Agent"),
    )

    await db.commit()

    reloaded_stmt = (
        select(DeficiencyNotice)
        .options(selectinload(DeficiencyNotice.items), selectinload(DeficiencyNotice.responses))
        .where(DeficiencyNotice.id == notice.id)
    )
    reloaded = (await db.execute(reloaded_stmt)).scalar_one()
    return reloaded


@router.get("/deficiencies/{notice_id}", response_model=DeficiencyNoticeResponse)
async def get_deficiency_notice(
    notice_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve full details of a specific deficiency notice."""
    stmt = (
        select(DeficiencyNotice)
        .options(selectinload(DeficiencyNotice.items), selectinload(DeficiencyNotice.responses))
        .where(DeficiencyNotice.id == notice_id)
    )
    notice = (await db.execute(stmt)).scalar_one_or_none()
    if not notice:
        raise NotFoundError("DeficiencyNotice", notice_id)

    user_roles = [r.code for r in current_user.roles]
    if "INSTITUTION_ADMIN" in user_roles and "SUPER_ADMIN" not in user_roles:
        if notice.institution_id != current_user.institution_id:
            raise PermissionDeniedError("Tenant violation: Access to notice denied.")

    return notice


@router.post("/deficiencies/{notice_id}/respond", response_model=DeficiencyNoticeResponse)
async def submit_institutional_clarification(
    notice_id: str,
    payload: DeficiencyResponseSubmit,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Submits official institutional clarification and links rectified replacement documents.
    Enforces:
    - Tenant ownership check
    - Notice state guard (must be ISSUED or REOPENED)
    - Statutory deadline validation
    - Transitions notice to RESPONSE_SUBMITTED and application to RESUBMITTED
    """
    stmt = (
        select(DeficiencyNotice)
        .options(selectinload(DeficiencyNotice.items), selectinload(DeficiencyNotice.responses))
        .where(DeficiencyNotice.id == notice_id)
    )
    notice = (await db.execute(stmt)).scalar_one_or_none()
    if not notice:
        raise NotFoundError("DeficiencyNotice", notice_id)

    user_roles = [r.code for r in current_user.roles]
    if "INSTITUTION_ADMIN" in user_roles and "SUPER_ADMIN" not in user_roles:
        if notice.institution_id != current_user.institution_id:
            raise PermissionDeniedError("Tenant boundary violation: Cannot respond to another institution's notice.")

    # State guard
    if notice.status not in ("ISSUED", "REOPENED"):
        raise ConflictError(f"Cannot submit response: Notice is currently in '{notice.status}' state.")

    # Statutory deadline check
    now = datetime.now(timezone.utc)
    # Notice due_date is timezone-aware
    notice_due = notice.due_date if notice.due_date.tzinfo else notice.due_date.replace(tzinfo=timezone.utc)
    if now > notice_due:
        raise ConflictError(
            f"Statutory cure deadline expired on {notice_due.strftime('%d-%b-%Y %H:%M UTC')}. Responses past deadline require formal extension from Regional Officer.",
            details={"expired_at": notice_due.isoformat(), "current_time": now.isoformat()},
        )

    # Record response
    resp = DeficiencyResponse(
        notice_id=notice.id,
        submitted_by_user_id=current_user.id,
        response_remarks=payload.response_remarks,
        attachments_json=json.dumps(payload.attachment_document_ids or []),
    )
    db.add(resp)
    notice.status = "RESPONSE_SUBMITTED"

    # Application state synchronization
    app_stmt = select(Application).where(Application.id == notice.application_id)
    app = (await db.execute(app_stmt)).scalar_one_or_none()
    if app and app.current_status == "DEFICIENCY_ISSUED":
        try:
            await WorkflowEngine.transition(
                db=db,
                application_id=app.id,
                target_status="RESUBMITTED",
                actor=current_user,
                remarks=f"Institution responded to deficiency notice {notice.notice_number}.",
                metadata={"notice_id": notice.id},
                ip_address=request.client.host if request.client else None,
            )
        except Exception:
            app.current_status = "RESUBMITTED"

    # Application event
    app_event = ApplicationEvent(
        application_id=notice.application_id,
        actor_id=current_user.id,
        event_type="DEFICIENCY_RESPONSE_SUBMITTED",
        remarks=f"Clarification submitted for notice {notice.notice_number}.",
    )
    db.add(app_event)

    # Chained audit event
    await record_audit_event(
        db=db,
        actor_id=current_user.id,
        action="SUBMIT_DEFICIENCY_RESPONSE",
        resource_type="DeficiencyNotice",
        resource_id=notice.id,
        details={"notice_number": notice.notice_number, "remarks": payload.response_remarks},
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("User-Agent"),
    )

    await db.commit()

    reloaded = (await db.execute(stmt)).scalar_one()
    return reloaded


@router.post("/deficiencies/{notice_id}/review", response_model=DeficiencyNoticeResponse)
async def review_and_resolve_deficiency(
    notice_id: str,
    payload: DeficiencyNoticeReview,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles("SCRUTINY_OFFICER", "REGIONAL_OFFICER", "SUPER_ADMIN")),
):
    """
    Officer review of institutional response:
    - Action RESOLVE: marks notice and items as RESOLVED. If application in RESUBMITTED, transitions back to UNDER_SCRUTINY.
    - Action REOPEN: re-opens notice for further correction.
    """
    stmt = (
        select(DeficiencyNotice)
        .options(selectinload(DeficiencyNotice.items), selectinload(DeficiencyNotice.responses))
        .where(DeficiencyNotice.id == notice_id)
    )
    notice = (await db.execute(stmt)).scalar_one_or_none()
    if not notice:
        raise NotFoundError("DeficiencyNotice", notice_id)

    action = payload.action.upper()
    now = datetime.now(timezone.utc)

    if action == "RESOLVE":
        notice.status = "RESOLVED"
        notice.resolved_at = now
        notice.officer_remarks = (notice.officer_remarks or "") + f"\n[Resolved by {current_user.full_name}]: {payload.officer_remarks}"
        for item in notice.items:
            item.item_status = "RESOLVED"

        # Check if application should resume scrutiny
        app_stmt = select(Application).where(Application.id == notice.application_id)
        app = (await db.execute(app_stmt)).scalar_one_or_none()
        if app and app.current_status == "RESUBMITTED":
            try:
                await WorkflowEngine.transition(
                    db=db,
                    application_id=app.id,
                    target_status="UNDER_SCRUTINY",
                    actor=current_user,
                    remarks=f"Deficiencies in notice {notice.notice_number} resolved. Scrutiny resumed.",
                    ip_address=request.client.host if request.client else None,
                )
            except Exception:
                app.current_status = "UNDER_SCRUTINY"

        # Notify institution
        notif = Notification(
            institution_id=notice.institution_id,
            title=f"Deficiency Notice Resolved: {notice.notice_number}",
            message=f"Deficiency notice {notice.notice_number} has been formally reviewed and cleared by scrutiny officers.",
            category="NOTICE_RESOLVED",
            link_url=f"/applications/{notice.application_id}",
            is_read=False,
            dedup_key=f"notice_resolved_{notice.id}",
        )
        db.add(notif)

    elif action == "REOPEN":
        notice.status = "REOPENED"
        # Grant statutory extension
        notice.due_date = now + timedelta(days=settings.DEFICIENCY_DEFAULT_CURE_DAYS)
        notice.officer_remarks = (notice.officer_remarks or "") + f"\n[Reopened by {current_user.full_name}]: {payload.officer_remarks}"

        notif = Notification(
            institution_id=notice.institution_id,
            title=f"Deficiency Notice Reopened: {notice.notice_number}",
            message=f"Additional clarification required for notice {notice.notice_number}. New due date: {notice.due_date.strftime('%d-%b-%Y')}.",
            category="DEFICIENCY_ISSUED",
            link_url=f"/applications/{notice.application_id}",
            is_read=False,
            dedup_key=f"notice_reopened_{notice.id}_{int(now.timestamp())}",
        )
        db.add(notif)
    else:
        raise ConflictError(f"Invalid review action '{payload.action}'. Expected RESOLVE or REOPEN.")

    # Chained audit event
    await record_audit_event(
        db=db,
        actor_id=current_user.id,
        action=f"DEFICIENCY_{action}",
        resource_type="DeficiencyNotice",
        resource_id=notice.id,
        details={"action": action, "remarks": payload.officer_remarks},
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("User-Agent"),
    )

    await db.commit()
    reloaded = (await db.execute(stmt)).scalar_one()
    return reloaded
