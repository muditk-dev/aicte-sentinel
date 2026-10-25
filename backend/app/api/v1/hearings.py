import json
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.core.exceptions import NotFoundError, ValidationError, PermissionDeniedError
from app.models.committee import Committee, Hearing, HearingDocket, HearingAttendance
from app.models.application import Application, ApplicationEvent
from app.models.institution import Institution
from app.models.user import User
from app.security.dependencies import get_current_user, require_roles
from app.schemas.committee import (
    HearingScheduleRequest,
    HearingResponse,
    HearingDocketCreate,
    HearingDocketResponse,
    HearingAttendanceRecord,
    HearingAttendanceResponse,
    HearingTransitionRequest,
    HearingMinutesRequest,
)
from app.audit.service import record_audit_event

router = APIRouter(prefix="/hearings", tags=["Committee Hearings & Dockets"])

ALLOWED_HEARING_TRANSITIONS = {
    "DRAFT": ["SCHEDULED", "CANCELLED"],
    "SCHEDULED": ["NOTICE_ISSUED", "POSTPONED", "CANCELLED"],
    "NOTICE_ISSUED": ["IN_SESSION", "POSTPONED", "CANCELLED"],
    "IN_SESSION": ["MINUTES_PENDING", "POSTPONED"],
    "MINUTES_PENDING": ["RECOMMENDATION_RECORDED"],
    "RECOMMENDATION_RECORDED": ["COMPLETED"],
    "POSTPONED": ["SCHEDULED", "CANCELLED"],
    "COMPLETED": [],
    "CANCELLED": [],
}


async def _serialize_hearing(db: AsyncSession, h: Hearing) -> HearingResponse:
    committee = await db.get(Committee, h.committee_id)
    
    # Dockets
    d_stmt = select(HearingDocket).where(HearingDocket.hearing_id == h.id)
    dockets = (await db.execute(d_stmt)).scalars().all()
    docket_dtos: List[HearingDocketResponse] = []
    for d in dockets:
        inst = await db.get(Institution, d.institution_id)
        app = await db.get(Application, d.application_id)
        docket_dtos.append(
            HearingDocketResponse(
                id=d.id,
                hearing_id=d.hearing_id,
                application_id=d.application_id,
                institution_id=d.institution_id,
                institution_name=inst.name if inst else None,
                application_number=app.application_number if app else None,
                docket_number=d.docket_number,
                matter_summary=d.matter_summary,
                referred_by=d.referred_by,
                institutional_representative_name=d.institutional_representative_name,
                docket_status=d.docket_status,
                docket_recommendation=d.docket_recommendation,
                docket_remarks=d.docket_remarks,
                created_at=d.created_at,
            )
        )

    # Attendances
    att_stmt = select(HearingAttendance).where(HearingAttendance.hearing_id == h.id)
    attendances = (await db.execute(att_stmt)).scalars().all()
    att_dtos: List[HearingAttendanceResponse] = [
        HearingAttendanceResponse(
            id=a.id,
            hearing_id=a.hearing_id,
            member_name=a.member_name,
            member_role=a.member_role,
            user_id=a.user_id,
            attended=a.attended,
            attendance_mode=a.attendance_mode,
            conflict_declared_for_docket_ids=a.conflict_declared_for_docket_ids,
            created_at=a.created_at,
        )
        for a in attendances
    ]

    return HearingResponse(
        id=h.id,
        committee_id=h.committee_id,
        committee_name=committee.name if committee else None,
        hearing_number=h.hearing_number,
        hearing_type=h.hearing_type,
        status=h.status,
        scheduled_date=h.scheduled_date,
        meeting_mode=h.meeting_mode,
        venue_or_link=h.venue_or_link,
        agenda=h.agenda,
        postponement_reason=h.postponement_reason,
        cancellation_reason=h.cancellation_reason,
        chairperson_name=h.chairperson_name,
        conducted_at=h.conducted_at,
        minutes_of_meeting=h.minutes_of_meeting,
        final_recommendation=h.final_recommendation,
        recommendation_summary=h.recommendation_summary,
        dockets=docket_dtos,
        attendances=att_dtos,
        created_at=h.created_at,
        updated_at=h.updated_at,
    )


@router.get("", response_model=List[HearingResponse])
async def list_hearings(
    committee_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    hearing_type: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Hearing)
    if committee_id:
        stmt = stmt.where(Hearing.committee_id == committee_id)
    if status:
        stmt = stmt.where(Hearing.status == status)
    if hearing_type:
        stmt = stmt.where(Hearing.hearing_type == hearing_type)

    stmt = stmt.order_by(Hearing.scheduled_date.desc())
    result = await db.execute(stmt)
    hearings = result.scalars().all()

    return [await _serialize_hearing(db, h) for h in hearings]


@router.post("", response_model=HearingResponse, dependencies=[Depends(require_roles("SUPER_ADMIN", "REGIONAL_OFFICER"))])
async def schedule_hearing(
    payload: HearingScheduleRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    committee = await db.get(Committee, payload.committee_id)
    if not committee:
        raise NotFoundError("Committee", payload.committee_id)

    timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d%H%M")
    hearing_number = f"HEAR-{payload.hearing_type}-{timestamp_str}"

    hearing = Hearing(
        committee_id=payload.committee_id,
        hearing_number=hearing_number,
        hearing_type=payload.hearing_type,
        status="SCHEDULED",
        scheduled_date=payload.scheduled_date,
        meeting_mode=payload.meeting_mode,
        venue_or_link=payload.venue_or_link,
        agenda=payload.agenda,
        chairperson_name=payload.chairperson_name,
    )
    db.add(hearing)
    await db.commit()
    await db.refresh(hearing)

    await record_audit_event(
        db=db,
        actor_id=current_user.id,
        action="HEARING_SESSION_SCHEDULED",
        resource_type="Hearing",
        resource_id=hearing.id,
        details={
            "hearing_number": hearing_number,
            "committee": committee.name,
            "date": payload.scheduled_date,
            "mode": payload.meeting_mode,
        },
    )

    return await _serialize_hearing(db, hearing)


@router.get("/{id}", response_model=HearingResponse)
async def get_hearing(
    id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    hearing = await db.get(Hearing, id)
    if not hearing:
        raise NotFoundError("Hearing", id)
    return await _serialize_hearing(db, hearing)


@router.post("/{id}/dockets", response_model=HearingDocketResponse, dependencies=[Depends(require_roles("SUPER_ADMIN", "REGIONAL_OFFICER"))])
async def add_docket_to_hearing(
    id: str,
    payload: HearingDocketCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    hearing = await db.get(Hearing, id)
    if not hearing:
        raise NotFoundError("Hearing", id)

    app = await db.get(Application, payload.application_id)
    if not app:
        raise NotFoundError("Application", payload.application_id)

    # Check for existing docket for this app in this hearing
    existing = (
        await db.execute(
            select(HearingDocket).where(
                HearingDocket.hearing_id == id,
                HearingDocket.application_id == payload.application_id,
            )
        )
    ).scalar_one_or_none()
    if existing:
        raise ValidationError("Application is already docketed for this hearing session.")

    docket_number = f"DKT-{hearing.hearing_number}-{app.application_number}"

    docket = HearingDocket(
        hearing_id=hearing.id,
        application_id=app.id,
        institution_id=app.institution_id,
        docket_number=docket_number,
        matter_summary=payload.matter_summary,
        referred_by=payload.referred_by,
        institutional_representative_name=payload.institutional_representative_name,
        docket_status="PENDING",
    )
    db.add(docket)

    # If application is in EVC_CONDUCTED or REJECTED (for appellate), update state if configured
    if app.current_status in ["EVC_CONDUCTED", "UNDER_SCRUTINY"]:
        app.current_status = "STANDING_HEARING"
        db.add(
            ApplicationEvent(
                application_id=app.id,
                actor_id=current_user.id,
                event_type="DOCKETED_FOR_HEARING",
                from_status="EVC_CONDUCTED",
                to_status="STANDING_HEARING",
                remarks=f"Docketed for {hearing.hearing_type} Hearing ({docket_number})",
                event_payload_json=json.dumps({"hearing_id": hearing.id, "docket_number": docket_number}),
            )
        )

    await db.commit()
    await db.refresh(docket)

    inst = await db.get(Institution, app.institution_id)
    return HearingDocketResponse(
        id=docket.id,
        hearing_id=docket.hearing_id,
        application_id=docket.application_id,
        institution_id=docket.institution_id,
        institution_name=inst.name if inst else None,
        application_number=app.application_number,
        docket_number=docket.docket_number,
        matter_summary=docket.matter_summary,
        referred_by=docket.referred_by,
        institutional_representative_name=docket.institutional_representative_name,
        docket_status=docket.docket_status,
        docket_recommendation=docket.docket_recommendation,
        docket_remarks=docket.docket_remarks,
        created_at=docket.created_at,
    )


@router.post("/{id}/attendance", response_model=List[HearingAttendanceResponse], dependencies=[Depends(require_roles("SUPER_ADMIN", "REGIONAL_OFFICER"))])
async def record_hearing_attendance(
    id: str,
    payload: List[HearingAttendanceRecord],
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    hearing = await db.get(Hearing, id)
    if not hearing:
        raise NotFoundError("Hearing", id)

    committee = await db.get(Committee, hearing.committee_id)
    attended_count = sum(1 for a in payload if a.attended)

    if committee and attended_count < committee.quorum_required:
        # Note quorum deficiency
        pass

    results: List[HearingAttendanceResponse] = []
    for att_in in payload:
        att = HearingAttendance(
            hearing_id=hearing.id,
            member_name=att_in.member_name,
            member_role=att_in.member_role,
            user_id=att_in.user_id,
            attended=att_in.attended,
            attendance_mode=att_in.attendance_mode,
            conflict_declared_for_docket_ids=att_in.conflict_declared_for_docket_ids,
        )
        db.add(att)
        await db.flush()
        results.append(
            HearingAttendanceResponse(
                id=att.id,
                hearing_id=att.hearing_id,
                member_name=att.member_name,
                member_role=att.member_role,
                user_id=att.user_id,
                attended=att.attended,
                attendance_mode=att.attendance_mode,
                conflict_declared_for_docket_ids=att.conflict_declared_for_docket_ids,
                created_at=att.created_at,
            )
        )

    await db.commit()
    return results


@router.post("/{id}/transition", response_model=HearingResponse, dependencies=[Depends(require_roles("SUPER_ADMIN", "REGIONAL_OFFICER"))])
async def transition_hearing_status(
    id: str,
    payload: HearingTransitionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    hearing = await db.get(Hearing, id)
    if not hearing:
        raise NotFoundError("Hearing", id)

    allowed = ALLOWED_HEARING_TRANSITIONS.get(hearing.status, [])
    if payload.target_status not in allowed:
        raise ValidationError(
            f"Invalid hearing transition from '{hearing.status}' to '{payload.target_status}'. Allowed: {allowed}"
        )

    old_status = hearing.status
    hearing.status = payload.target_status
    if payload.target_status == "IN_SESSION":
        hearing.conducted_at = datetime.now(timezone.utc).isoformat()
    elif payload.target_status == "POSTPONED":
        hearing.postponement_reason = payload.reason
    elif payload.target_status == "CANCELLED":
        hearing.cancellation_reason = payload.reason

    await db.commit()
    await db.refresh(hearing)

    await record_audit_event(
        db=db,
        actor_id=current_user.id,
        action="HEARING_STATUS_TRANSITION",
        resource_type="Hearing",
        resource_id=hearing.id,
        details={"from": old_status, "to": payload.target_status, "reason": payload.reason},
    )

    return await _serialize_hearing(db, hearing)


@router.post("/{id}/minutes", response_model=HearingResponse, dependencies=[Depends(require_roles("SUPER_ADMIN", "REGIONAL_OFFICER"))])
async def record_hearing_minutes(
    id: str,
    payload: HearingMinutesRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    hearing = await db.get(Hearing, id)
    if not hearing:
        raise NotFoundError("Hearing", id)

    # Validate Quorum
    committee = await db.get(Committee, hearing.committee_id)
    att_stmt = select(HearingAttendance).where(HearingAttendance.hearing_id == id, HearingAttendance.attended.is_(True))
    present_members = (await db.execute(att_stmt)).scalars().all()
    if committee and len(present_members) < committee.quorum_required:
        raise ValidationError(
            f"Statutory Quorum not met: Required {committee.quorum_required} members, but only {len(present_members)} attended."
        )

    hearing.minutes_of_meeting = payload.minutes_of_meeting
    hearing.final_recommendation = payload.final_recommendation
    hearing.recommendation_summary = payload.recommendation_summary
    hearing.status = "RECOMMENDATION_RECORDED"

    # Update individual docket outcomes if provided
    if payload.docket_outcomes:
        for item in payload.docket_outcomes:
            d_id = item.get("docket_id")
            if d_id:
                docket = await db.get(HearingDocket, d_id)
                if docket and docket.hearing_id == id:
                    docket.docket_status = item.get("status", "DECIDED")
                    docket.docket_recommendation = item.get("recommendation")
                    docket.docket_remarks = item.get("remarks")

    await db.commit()
    await db.refresh(hearing)

    await record_audit_event(
        db=db,
        actor_id=current_user.id,
        action="HEARING_MINUTES_RECORDED",
        resource_type="Hearing",
        resource_id=hearing.id,
        details={
            "hearing_number": hearing.hearing_number,
            "final_recommendation": payload.final_recommendation,
            "quorum_present": len(present_members),
        },
    )

    return await _serialize_hearing(db, hearing)
