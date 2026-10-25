import json
import hashlib
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from app.core.database import get_db
from app.core.exceptions import NotFoundError, PermissionDeniedError, ValidationError
from app.models.evc import EVCInspection, EVCInspectionExpert, EVCReportVersion, Expert
from app.models.application import Application, ApplicationEvent
from app.models.institution import Institution
from app.models.user import User
from app.security.dependencies import get_current_user, require_roles
from app.schemas.evc import (
    EVCInspectionCreate,
    EVCInspectionResponse,
    EVCExpertAssignRequest,
    EVCPanelMemberResponse,
    EVCReportSubmit,
    EVCReportReviewRequest,
    EVCReportVersionResponse,
    InspectionTransitionRequest,
)
from app.services.conflict_service import ConflictChecker
from app.audit.service import record_audit_event

router = APIRouter(prefix="/inspections", tags=["EVC Inspection Operations"])

ALLOWED_INSPECTION_TRANSITIONS = {
    "DRAFT": ["SCHEDULED", "CANCELLED"],
    "SCHEDULED": ["IN_PROGRESS", "CANCELLED"],
    "IN_PROGRESS": ["REPORT_SUBMITTED", "CANCELLED"],
    "REPORT_SUBMITTED": ["UNDER_REVIEW"],
    "UNDER_REVIEW": ["ACCEPTED", "RETURNED_FOR_CORRECTION"],
    "RETURNED_FOR_CORRECTION": ["REPORT_SUBMITTED", "CANCELLED"],
    "ACCEPTED": [],
    "CANCELLED": [],
}


async def _serialize_inspection(db: AsyncSession, inspection: EVCInspection) -> EVCInspectionResponse:
    # Fetch Institution name
    inst = await db.get(Institution, inspection.institution_id)
    chairperson = await db.get(Expert, inspection.chairperson_id) if inspection.chairperson_id else None

    # Fetch panel members
    pm_stmt = select(EVCInspectionExpert).where(EVCInspectionExpert.inspection_id == inspection.id)
    pm_records = (await db.execute(pm_stmt)).scalars().all()

    panel_members: List[EVCPanelMemberResponse] = []
    for pm in pm_records:
        expert = await db.get(Expert, pm.expert_id)
        panel_members.append(
            EVCPanelMemberResponse(
                id=pm.id,
                inspection_id=pm.inspection_id,
                expert_id=pm.expert_id,
                expert_name=expert.name if expert else "Unknown",
                expert_designation=expert.designation if expert else "",
                expert_organization=expert.organization if expert else "",
                role=pm.role,
                conflict_check_passed=pm.conflict_check_passed,
                conflict_notes=pm.conflict_notes,
                attendance_status=pm.attendance_status,
                attendance_timestamp=pm.attendance_timestamp,
                sign_off_status=pm.sign_off_status,
                sign_off_timestamp=pm.sign_off_timestamp,
                sign_off_remarks=pm.sign_off_remarks,
            )
        )

    # Fetch latest report version
    rep_stmt = (
        select(EVCReportVersion)
        .where(EVCReportVersion.inspection_id == inspection.id)
        .order_by(EVCReportVersion.version_number.desc())
    )
    latest_rep = (await db.execute(rep_stmt)).scalars().first()
    latest_report_dto = None
    if latest_rep:
        submitter = await db.get(User, latest_rep.submitted_by_user_id)
        reviewer = await db.get(User, latest_rep.reviewed_by_user_id) if latest_rep.reviewed_by_user_id else None
        
        try:
            chk_data = json.loads(latest_rep.checklist_data_json or "{}")
        except Exception:
            chk_data = {}
        try:
            ev_refs = json.loads(latest_rep.evidence_references_json or "[]")
        except Exception:
            ev_refs = []
        try:
            loc_ev = json.loads(latest_rep.location_evidence_json or "{}")
        except Exception:
            loc_ev = {}
        try:
            virt_att = json.loads(latest_rep.virtual_attendance_json or "{}")
        except Exception:
            virt_att = {}

        latest_report_dto = EVCReportVersionResponse(
            id=latest_rep.id,
            inspection_id=latest_rep.inspection_id,
            version_number=latest_rep.version_number,
            application_id=latest_rep.application_id,
            submitted_by_user_id=latest_rep.submitted_by_user_id,
            submitted_by_name=submitter.full_name if submitter else None,
            submitted_at=latest_rep.submitted_at,
            sha256_hash=latest_rep.sha256_hash,
            overall_recommendation=latest_rep.overall_recommendation,
            infrastructure_score=latest_rep.infrastructure_score,
            faculty_verification_status=latest_rep.faculty_verification_status,
            land_building_status=latest_rep.land_building_status,
            laboratories_equipment_status=latest_rep.laboratories_equipment_status,
            safety_and_amenities_status=latest_rep.safety_and_amenities_status,
            observations=latest_rep.observations,
            deficiencies_identified=latest_rep.deficiencies_identified,
            checklist_data=chk_data,
            evidence_references=ev_refs,
            location_evidence=loc_ev,
            virtual_attendance=virt_att,
            review_status=latest_rep.review_status,
            reviewed_by_user_id=latest_rep.reviewed_by_user_id,
            reviewed_by_name=reviewer.full_name if reviewer else None,
            reviewed_at=latest_rep.reviewed_at,
            review_remarks=latest_rep.review_remarks,
            created_at=latest_rep.created_at,
        )

    return EVCInspectionResponse(
        id=inspection.id,
        application_id=inspection.application_id,
        institution_id=inspection.institution_id,
        institution_name=inst.name if inst else None,
        inspection_number=inspection.inspection_number,
        inspection_mode=inspection.inspection_mode,
        status=inspection.status,
        scheduled_start_date=inspection.scheduled_start_date,
        scheduled_end_date=inspection.scheduled_end_date,
        actual_inspection_date=inspection.actual_inspection_date,
        chairperson_id=inspection.chairperson_id,
        chairperson_name=chairperson.name if chairperson else None,
        meeting_link=inspection.meeting_link,
        location_coordinates=inspection.location_coordinates,
        location_address=inspection.location_address,
        cancellation_reason=inspection.cancellation_reason,
        assigned_by_user_id=inspection.assigned_by_user_id,
        panel_members=panel_members,
        latest_report=latest_report_dto,
        created_at=inspection.created_at,
        updated_at=inspection.updated_at,
    )


@router.get("", response_model=List[EVCInspectionResponse])
async def list_inspections(
    application_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    mode: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Lists inspections with multi-tenant data isolation for institutions."""
    stmt = select(EVCInspection)
    user_roles = [r.code for r in current_user.roles]

    if "INSTITUTION_ADMIN" in user_roles and current_user.institution_id:
        stmt = stmt.where(EVCInspection.institution_id == current_user.institution_id)

    if application_id:
        stmt = stmt.where(EVCInspection.application_id == application_id)
    if status:
        stmt = stmt.where(EVCInspection.status == status)
    if mode:
        stmt = stmt.where(EVCInspection.inspection_mode == mode)

    stmt = stmt.order_by(EVCInspection.created_at.desc())
    result = await db.execute(stmt)
    inspections = result.scalars().all()

    return [await _serialize_inspection(db, insp) for insp in inspections]


@router.post("", response_model=EVCInspectionResponse, dependencies=[Depends(require_roles("SUPER_ADMIN", "REGIONAL_OFFICER"))])
async def create_inspection(
    payload: EVCInspectionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Creates a formal EVC inspection assignment for an application."""
    stmt = select(Application).where(Application.id == payload.application_id)
    result = await db.execute(stmt)
    app = result.scalar_one_or_none()
    if not app:
        raise NotFoundError("Application", payload.application_id)

    # Check for active conflicting inspection for this application
    active_insp_stmt = select(EVCInspection).where(
        EVCInspection.application_id == app.id,
        EVCInspection.status.in_(["DRAFT", "SCHEDULED", "IN_PROGRESS", "REPORT_SUBMITTED", "UNDER_REVIEW"]),
    )
    active_insp = (await db.execute(active_insp_stmt)).scalar_one_or_none()
    if active_insp:
        raise ValidationError(
            f"An active inspection ({active_insp.inspection_number}) is already in progress for this application."
        )

    timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d%H%M")
    inspection_number = f"EVC-{app.application_number}-{timestamp_str}"

    inspection = EVCInspection(
        application_id=app.id,
        institution_id=app.institution_id,
        inspection_number=inspection_number,
        inspection_mode=payload.inspection_mode,
        status="SCHEDULED",
        scheduled_start_date=payload.scheduled_start_date,
        scheduled_end_date=payload.scheduled_end_date,
        chairperson_id=payload.chairperson_id,
        meeting_link=payload.meeting_link,
        location_coordinates=payload.location_coordinates,
        location_address=payload.location_address,
        assigned_by_user_id=current_user.id,
    )
    db.add(inspection)

    # Auto-transition application status to EVC_SCHEDULED if applicable
    if app.current_status in ["SUBMITTED", "UNDER_SCRUTINY"]:
        app.current_status = "EVC_SCHEDULED"
        event = ApplicationEvent(
            application_id=app.id,
            actor_id=current_user.id,
            event_type="EVC_SCHEDULED",
            from_status="UNDER_SCRUTINY",
            to_status="EVC_SCHEDULED",
            remarks=f"EVC Inspection {inspection_number} scheduled ({payload.inspection_mode})",
            event_payload_json=json.dumps({"inspection_id": inspection.id, "mode": payload.inspection_mode}),
        )
        db.add(event)

    await db.commit()
    await db.refresh(inspection)

    await record_audit_event(
        db=db,
        actor_id=current_user.id,
        action="EVC_INSPECTION_SCHEDULED",
        resource_type="EVCInspection",
        resource_id=inspection.id,
        details={
            "inspection_number": inspection_number,
            "application_id": app.id,
            "mode": payload.inspection_mode,
            "start": payload.scheduled_start_date,
        },
    )

    return await _serialize_inspection(db, inspection)


@router.get("/{id}", response_model=EVCInspectionResponse)
async def get_inspection(
    id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    inspection = await db.get(EVCInspection, id)
    if not inspection:
        raise NotFoundError("EVCInspection", id)

    # Tenant boundary
    user_roles = [r.code for r in current_user.roles]
    if "INSTITUTION_ADMIN" in user_roles and current_user.institution_id != inspection.institution_id:
        raise PermissionDeniedError("Unauthorized access to another institution's inspection docket.")

    return await _serialize_inspection(db, inspection)


@router.post("/{id}/experts", response_model=EVCPanelMemberResponse, dependencies=[Depends(require_roles("SUPER_ADMIN", "REGIONAL_OFFICER"))])
async def assign_expert_to_panel(
    id: str,
    payload: EVCExpertAssignRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Assigns an expert to the inspection panel with mandatory conflict verification."""
    inspection = await db.get(EVCInspection, id)
    if not inspection:
        raise NotFoundError("EVCInspection", id)

    expert = await db.get(Expert, payload.expert_id)
    if not expert:
        raise NotFoundError("Expert", payload.expert_id)

    # Check if expert is already assigned
    existing_stmt = select(EVCInspectionExpert).where(
        EVCInspectionExpert.inspection_id == id,
        EVCInspectionExpert.expert_id == payload.expert_id,
    )
    existing = (await db.execute(existing_stmt)).scalar_one_or_none()
    if existing:
        raise ValidationError(f"Expert {expert.name} is already assigned to this inspection panel.")

    # 1. Conflict of Interest Check
    has_conflict, is_blocked, reasons, policy_version, _ = await ConflictChecker.evaluate_conflict(
        db=db,
        expert_id=payload.expert_id,
        application_id=inspection.application_id,
    )

    conflict_passed = not has_conflict
    conflict_notes = None

    if has_conflict:
        if not payload.override_conflict:
            raise ValidationError(
                f"Statutory Conflict of Interest detected under {policy_version}: "
                + "; ".join(reasons)
                + ". Assignment blocked. A documented reviewer justification is required to override."
            )
        else:
            if not payload.override_justification or len(payload.override_justification.strip()) < 10:
                raise ValidationError("A documented justification (min 10 chars) is mandatory to override conflict.")
            conflict_notes = f"OVERRIDDEN by {current_user.full_name}: {payload.override_justification.strip()} | Detected: {'; '.join(reasons)}"
            conflict_passed = True

    # 2. Scheduling Conflict Check
    # Verify expert has no active overlapping inspection
    sched_stmt = (
        select(EVCInspectionExpert)
        .join(EVCInspection, EVCInspectionExpert.inspection_id == EVCInspection.id)
        .where(
            EVCInspectionExpert.expert_id == payload.expert_id,
            EVCInspection.status.in_(["SCHEDULED", "IN_PROGRESS"]),
            EVCInspection.id != inspection.id,
            EVCInspection.scheduled_start_date <= inspection.scheduled_end_date,
            EVCInspection.scheduled_end_date >= inspection.scheduled_start_date,
        )
    )
    conflict_sched = (await db.execute(sched_stmt)).scalar_one_or_none()
    if conflict_sched:
        raise ValidationError(
            f"Scheduling conflict: Expert {expert.name} is already committed to an overlapping inspection schedule."
        )

    panel_member = EVCInspectionExpert(
        inspection_id=inspection.id,
        expert_id=expert.id,
        role=payload.role,
        conflict_check_passed=conflict_passed,
        conflict_notes=conflict_notes,
        attendance_status="PENDING",
        sign_off_status="PENDING",
    )
    db.add(panel_member)

    # Set as chairperson if role is CHAIRPERSON
    if payload.role == "CHAIRPERSON":
        inspection.chairperson_id = expert.id

    await db.commit()
    await db.refresh(panel_member)

    await record_audit_event(
        db=db,
        actor_id=current_user.id,
        action="EVC_PANEL_EXPERT_ASSIGNED",
        resource_type="EVCInspectionExpert",
        resource_id=panel_member.id,
        details={
            "inspection_id": inspection.id,
            "expert_name": expert.name,
            "role": payload.role,
            "conflict_overridden": payload.override_conflict,
            "conflict_notes": conflict_notes,
        },
    )

    return EVCPanelMemberResponse(
        id=panel_member.id,
        inspection_id=panel_member.inspection_id,
        expert_id=panel_member.expert_id,
        expert_name=expert.name,
        expert_designation=expert.designation,
        expert_organization=expert.organization,
        role=panel_member.role,
        conflict_check_passed=panel_member.conflict_check_passed,
        conflict_notes=panel_member.conflict_notes,
        attendance_status=panel_member.attendance_status,
        attendance_timestamp=panel_member.attendance_timestamp,
        sign_off_status=panel_member.sign_off_status,
        sign_off_timestamp=panel_member.sign_off_timestamp,
        sign_off_remarks=panel_member.sign_off_remarks,
    )


@router.post("/{id}/transition", response_model=EVCInspectionResponse)
async def transition_inspection_state(
    id: str,
    payload: InspectionTransitionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Guarded inspection state transition."""
    inspection = await db.get(EVCInspection, id)
    if not inspection:
        raise NotFoundError("EVCInspection", id)

    allowed_targets = ALLOWED_INSPECTION_TRANSITIONS.get(inspection.status, [])
    if payload.target_status not in allowed_targets:
        raise ValidationError(
            f"Invalid transition from '{inspection.status}' to '{payload.target_status}'. Allowed: {allowed_targets}"
        )

    user_roles = [r.code for r in current_user.roles]
    # Check authorization
    if "SUPER_ADMIN" not in user_roles and "REGIONAL_OFFICER" not in user_roles:
        # Check if expert assigned
        pm_stmt = select(EVCInspectionExpert).where(
            EVCInspectionExpert.inspection_id == id,
            EVCInspectionExpert.expert_id.in_(
                select(Expert.id).where(Expert.user_id == current_user.id)
            ),
        )
        is_assigned = (await db.execute(pm_stmt)).scalar_one_or_none()
        if not is_assigned:
            raise PermissionDeniedError("Only assigned experts or regional officers may transition inspection state.")

    old_status = inspection.status
    inspection.status = payload.target_status
    if payload.target_status == "IN_PROGRESS":
        inspection.actual_inspection_date = datetime.now(timezone.utc).isoformat()
    elif payload.target_status == "CANCELLED":
        inspection.cancellation_reason = payload.remarks

    await db.commit()
    await db.refresh(inspection)

    await record_audit_event(
        db=db,
        actor_id=current_user.id,
        action="INSPECTION_STATE_TRANSITION",
        resource_type="EVCInspection",
        resource_id=inspection.id,
        details={"from": old_status, "to": payload.target_status, "remarks": payload.remarks},
    )

    return await _serialize_inspection(db, inspection)


@router.post("/{id}/reports", response_model=EVCReportVersionResponse)
async def submit_inspection_report(
    id: str,
    payload: EVCReportSubmit,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Submits a versioned inspection report with SHA-256 payload digest."""
    inspection = await db.get(EVCInspection, id)
    if not inspection:
        raise NotFoundError("EVCInspection", id)

    if inspection.status not in ["SCHEDULED", "IN_PROGRESS", "RETURNED_FOR_CORRECTION"]:
        raise ValidationError(f"Cannot submit report while inspection is in state '{inspection.status}'.")

    # Determine next version number
    v_stmt = (
        select(EVCReportVersion.version_number)
        .where(EVCReportVersion.inspection_id == id)
        .order_by(EVCReportVersion.version_number.desc())
    )
    latest_v = (await db.execute(v_stmt)).scalars().first() or 0
    next_version = latest_v + 1

    now_iso = datetime.now(timezone.utc).isoformat()

    # Calculate SHA-256 digest of canonical report payload
    canonical_payload = (
        f"{inspection.id}:{next_version}:{payload.overall_recommendation}:"
        f"{payload.observations.strip()}:{json.dumps(payload.checklist_data, sort_keys=True)}:"
        f"{now_iso}:{current_user.id}"
    )
    sha256_hash = hashlib.sha256(canonical_payload.encode("utf-8")).hexdigest()

    report_version = EVCReportVersion(
        inspection_id=inspection.id,
        version_number=next_version,
        application_id=inspection.application_id,
        submitted_by_user_id=current_user.id,
        submitted_at=now_iso,
        sha256_hash=sha256_hash,
        overall_recommendation=payload.overall_recommendation,
        infrastructure_score=payload.infrastructure_score,
        faculty_verification_status=payload.faculty_verification_status,
        land_building_status=payload.land_building_status,
        laboratories_equipment_status=payload.laboratories_equipment_status,
        safety_and_amenities_status=payload.safety_and_amenities_status,
        observations=payload.observations,
        deficiencies_identified=payload.deficiencies_identified,
        checklist_data_json=json.dumps(payload.checklist_data),
        evidence_references_json=json.dumps(payload.evidence_references),
        location_evidence_json=json.dumps(payload.location_evidence),
        virtual_attendance_json=json.dumps(payload.virtual_attendance),
        review_status="PENDING",
    )
    db.add(report_version)

    inspection.status = "REPORT_SUBMITTED"

    # Also update application status to EVC_CONDUCTED if in EVC_SCHEDULED
    app = await db.get(Application, inspection.application_id)
    if app and app.current_status == "EVC_SCHEDULED":
        app.current_status = "EVC_CONDUCTED"
        event = ApplicationEvent(
            application_id=app.id,
            actor_id=current_user.id,
            event_type="EVC_REPORT_SUBMITTED",
            from_status="EVC_SCHEDULED",
            to_status="EVC_CONDUCTED",
            remarks=f"EVC Report v{next_version} submitted ({payload.overall_recommendation})",
            event_payload_json=json.dumps({"sha256": sha256_hash, "version": next_version}),
        )
        db.add(event)

    await db.commit()
    await db.refresh(report_version)

    await record_audit_event(
        db=db,
        actor_id=current_user.id,
        action="EVC_REPORT_SUBMITTED",
        resource_type="EVCReportVersion",
        resource_id=report_version.id,
        details={
            "inspection_id": inspection.id,
            "version": next_version,
            "sha256": sha256_hash,
            "recommendation": payload.overall_recommendation,
        },
    )

    return EVCReportVersionResponse(
        id=report_version.id,
        inspection_id=report_version.inspection_id,
        version_number=report_version.version_number,
        application_id=report_version.application_id,
        submitted_by_user_id=report_version.submitted_by_user_id,
        submitted_by_name=current_user.full_name,
        submitted_at=report_version.submitted_at,
        sha256_hash=report_version.sha256_hash,
        overall_recommendation=report_version.overall_recommendation,
        infrastructure_score=report_version.infrastructure_score,
        faculty_verification_status=report_version.faculty_verification_status,
        land_building_status=report_version.land_building_status,
        laboratories_equipment_status=report_version.laboratories_equipment_status,
        safety_and_amenities_status=report_version.safety_and_amenities_status,
        observations=report_version.observations,
        deficiencies_identified=report_version.deficiencies_identified,
        checklist_data=payload.checklist_data,
        evidence_references=payload.evidence_references,
        location_evidence=payload.location_evidence,
        virtual_attendance=payload.virtual_attendance,
        review_status=report_version.review_status,
        reviewed_by_user_id=None,
        reviewed_by_name=None,
        reviewed_at=None,
        review_remarks=None,
        created_at=report_version.created_at,
    )


@router.get("/{id}/reports", response_model=List[EVCReportVersionResponse])
async def list_report_versions(
    id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(EVCReportVersion)
        .where(EVCReportVersion.inspection_id == id)
        .order_by(EVCReportVersion.version_number.desc())
    )
    reports = (await db.execute(stmt)).scalars().all()

    res = []
    for r in reports:
        sub = await db.get(User, r.submitted_by_user_id)
        rev = await db.get(User, r.reviewed_by_user_id) if r.reviewed_by_user_id else None
        res.append(
            EVCReportVersionResponse(
                id=r.id,
                inspection_id=r.inspection_id,
                version_number=r.version_number,
                application_id=r.application_id,
                submitted_by_user_id=r.submitted_by_user_id,
                submitted_by_name=sub.full_name if sub else None,
                submitted_at=r.submitted_at,
                sha256_hash=r.sha256_hash,
                overall_recommendation=r.overall_recommendation,
                infrastructure_score=r.infrastructure_score,
                faculty_verification_status=r.faculty_verification_status,
                land_building_status=r.land_building_status,
                laboratories_equipment_status=r.laboratories_equipment_status,
                safety_and_amenities_status=r.safety_and_amenities_status,
                observations=r.observations,
                deficiencies_identified=r.deficiencies_identified,
                checklist_data=json.loads(r.checklist_data_json or "{}"),
                evidence_references=json.loads(r.evidence_references_json or "[]"),
                location_evidence=json.loads(r.location_evidence_json or "{}"),
                virtual_attendance=json.loads(r.virtual_attendance_json or "{}"),
                review_status=r.review_status,
                reviewed_by_user_id=r.reviewed_by_user_id,
                reviewed_by_name=rev.full_name if rev else None,
                reviewed_at=r.reviewed_at,
                review_remarks=r.review_remarks,
                created_at=r.created_at,
            )
        )
    return res


@router.post("/{id}/reports/{version_id}/review", response_model=EVCReportVersionResponse, dependencies=[Depends(require_roles("SUPER_ADMIN", "REGIONAL_OFFICER"))])
async def review_inspection_report(
    id: str,
    version_id: str,
    payload: EVCReportReviewRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Reviews an EVC report version (ACCEPTED or RETURNED_FOR_CORRECTION)."""
    inspection = await db.get(EVCInspection, id)
    if not inspection:
        raise NotFoundError("EVCInspection", id)

    report = await db.get(EVCReportVersion, version_id)
    if not report or report.inspection_id != id:
        raise NotFoundError("EVCReportVersion", version_id)

    now_iso = datetime.now(timezone.utc).isoformat()
    report.review_status = payload.review_status
    report.reviewed_by_user_id = current_user.id
    report.reviewed_at = now_iso
    report.review_remarks = payload.review_remarks

    if payload.review_status == "ACCEPTED":
        inspection.status = "ACCEPTED"
    elif payload.review_status == "RETURNED_FOR_CORRECTION":
        inspection.status = "RETURNED_FOR_CORRECTION"

    await db.commit()
    await db.refresh(report)

    await record_audit_event(
        db=db,
        actor_id=current_user.id,
        action=f"EVC_REPORT_REVIEW_{payload.review_status}",
        resource_type="EVCReportVersion",
        resource_id=report.id,
        details={
            "inspection_id": inspection.id,
            "version": report.version_number,
            "decision": payload.review_status,
            "remarks": payload.review_remarks,
        },
    )

    sub = await db.get(User, report.submitted_by_user_id)
    return EVCReportVersionResponse(
        id=report.id,
        inspection_id=report.inspection_id,
        version_number=report.version_number,
        application_id=report.application_id,
        submitted_by_user_id=report.submitted_by_user_id,
        submitted_by_name=sub.full_name if sub else None,
        submitted_at=report.submitted_at,
        sha256_hash=report.sha256_hash,
        overall_recommendation=report.overall_recommendation,
        infrastructure_score=report.infrastructure_score,
        faculty_verification_status=report.faculty_verification_status,
        land_building_status=report.land_building_status,
        laboratories_equipment_status=report.laboratories_equipment_status,
        safety_and_amenities_status=report.safety_and_amenities_status,
        observations=report.observations,
        deficiencies_identified=report.deficiencies_identified,
        checklist_data=json.loads(report.checklist_data_json or "{}"),
        evidence_references=json.loads(report.evidence_references_json or "[]"),
        location_evidence=json.loads(report.location_evidence_json or "{}"),
        virtual_attendance=json.loads(report.virtual_attendance_json or "{}"),
        review_status=report.review_status,
        reviewed_by_user_id=report.reviewed_by_user_id,
        reviewed_by_name=current_user.full_name,
        reviewed_at=report.reviewed_at,
        review_remarks=report.review_remarks,
        created_at=report.created_at,
    )
