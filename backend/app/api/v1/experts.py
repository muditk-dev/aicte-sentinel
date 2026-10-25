import json
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.core.exceptions import NotFoundError, PermissionDeniedError
from app.models.evc import Expert
from app.models.user import User
from app.security.dependencies import get_current_user, require_roles
from app.schemas.evc import (
    ExpertCreate,
    ExpertResponse,
    ConflictCheckRequest,
    ConflictCheckResponse,
)
from app.services.conflict_service import ConflictChecker
from app.audit.service import record_audit_event

router = APIRouter(prefix="/experts", tags=["EVC Experts Registry"])


def _serialize_expert(expert: Expert, is_officer: bool) -> ExpertResponse:
    specializations = []
    try:
        specializations = json.loads(expert.specializations_json or "[]")
    except Exception:
        pass

    affiliated_ids = []
    try:
        affiliated_ids = json.loads(expert.affiliated_institution_ids_json or "[]")
    except Exception:
        pass

    conflicts = []
    if is_officer:
        try:
            conflicts = json.loads(expert.conflict_declarations_json or "[]")
        except Exception:
            pass

    return ExpertResponse(
        id=expert.id,
        user_id=expert.user_id,
        name=expert.name,
        email=expert.email,
        phone=expert.phone if is_officer else None,
        designation=expert.designation,
        organization=expert.organization,
        expert_type=expert.expert_type,
        qualifications=expert.qualifications,
        experience_years=expert.experience_years,
        specializations=specializations,
        affiliated_institution_ids=affiliated_ids if is_officer else [],
        alma_mater=expert.alma_mater,
        state=expert.state,
        district=expert.district,
        availability_status=expert.availability_status,
        conflict_declarations=conflicts,
        is_active=expert.is_active,
        verification_status=expert.verification_status,
        created_at=expert.created_at,
        updated_at=expert.updated_at,
    )


@router.get("", response_model=List[ExpertResponse])
async def list_experts(
    expert_type: Optional[str] = Query(None),
    availability: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    district: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Lists registered EVC experts with role-based masking of sensitive conflict data."""
    is_officer = any(r.code in ["SUPER_ADMIN", "REGIONAL_OFFICER", "SCRUTINY_OFFICER"] for r in current_user.roles)

    stmt = select(Expert).where(Expert.is_active.is_(True))
    if expert_type:
        stmt = stmt.where(Expert.expert_type == expert_type)
    if availability:
        stmt = stmt.where(Expert.availability_status == availability)
    if state:
        stmt = stmt.where(Expert.state == state)
    if district:
        stmt = stmt.where(Expert.district == district)

    stmt = stmt.order_by(Expert.name)
    result = await db.execute(stmt)
    experts = result.scalars().all()

    return [_serialize_expert(e, is_officer) for e in experts]


@router.post("", response_model=ExpertResponse, dependencies=[Depends(require_roles("SUPER_ADMIN", "REGIONAL_OFFICER"))])
async def create_expert(
    payload: ExpertCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Registers a new technical/academic expert into the national EVC roster."""
    expert = Expert(
        user_id=payload.user_id,
        name=payload.name,
        email=payload.email,
        phone=payload.phone,
        designation=payload.designation,
        organization=payload.organization,
        expert_type=payload.expert_type,
        qualifications=payload.qualifications,
        experience_years=payload.experience_years,
        specializations_json=json.dumps(payload.specializations),
        affiliated_institution_ids_json=json.dumps(payload.affiliated_institution_ids),
        alma_mater=payload.alma_mater,
        state=payload.state,
        district=payload.district,
        availability_status=payload.availability_status,
        conflict_declarations_json=json.dumps(payload.conflict_declarations),
        is_active=True,
        verification_status="VERIFIED",
    )
    db.add(expert)
    await db.commit()
    await db.refresh(expert)

    await record_audit_event(
        db=db,
        actor_id=current_user.id,
        action="EXPERT_REGISTERED",
        resource_type="Expert",
        resource_id=expert.id,
        details={"name": expert.name, "organization": expert.organization, "expert_type": expert.expert_type},
    )

    return _serialize_expert(expert, is_officer=True)


@router.get("/{id}", response_model=ExpertResponse)
async def get_expert(
    id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    expert = await db.get(Expert, id)
    if not expert:
        raise NotFoundError("Expert", id)

    is_officer = any(r.code in ["SUPER_ADMIN", "REGIONAL_OFFICER", "SCRUTINY_OFFICER"] for r in current_user.roles)
    return _serialize_expert(expert, is_officer)


@router.post("/{id}/conflict-check", response_model=ConflictCheckResponse)
async def check_expert_conflict(
    id: str,
    payload: ConflictCheckRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Evaluates conflict of interest rules against a specific application."""
    has_conflict, is_blocked, reasons, policy_version, institution = await ConflictChecker.evaluate_conflict(
        db=db,
        expert_id=id,
        application_id=payload.application_id,
    )
    expert = await db.get(Expert, id)

    return ConflictCheckResponse(
        expert_id=id,
        expert_name=expert.name if expert else "Unknown",
        application_id=payload.application_id,
        institution_id=institution.id,
        institution_name=institution.name,
        has_conflict=has_conflict,
        is_blocked=is_blocked,
        policy_version=policy_version,
        conflict_reasons=reasons,
    )
