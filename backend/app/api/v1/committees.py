import json
from typing import List, Optional
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.core.exceptions import NotFoundError, ValidationError
from app.models.committee import Committee, CommitteeMembership
from app.models.user import User
from app.security.dependencies import get_current_user, require_roles
from app.schemas.committee import (
    CommitteeCreate,
    CommitteeResponse,
    CommitteeMemberCreate,
    CommitteeMembershipResponse,
)
from app.audit.service import record_audit_event

router = APIRouter(prefix="/committees", tags=["Standing Committees (SHC/SAC)"])


def _serialize_committee(c: Committee) -> CommitteeResponse:
    members = []
    for m in c.memberships:
        try:
            conflicts = json.loads(m.conflict_declarations_json or "[]")
        except Exception:
            conflicts = []
        members.append(
            CommitteeMembershipResponse(
                id=m.id,
                committee_id=m.committee_id,
                user_id=m.user_id,
                expert_id=m.expert_id,
                member_name=m.member_name,
                member_role=m.member_role,
                conflict_declarations=conflicts,
                is_active=m.is_active,
                created_at=m.created_at,
            )
        )

    return CommitteeResponse(
        id=c.id,
        code=c.code,
        name=c.name,
        committee_type=c.committee_type,
        description=c.description,
        quorum_required=c.quorum_required,
        is_active=c.is_active,
        valid_from=c.valid_from,
        valid_to=c.valid_to,
        memberships=members,
        created_at=c.created_at,
        updated_at=c.updated_at,
    )


@router.get("", response_model=List[CommitteeResponse])
async def list_committees(
    committee_type: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Committee).where(Committee.is_active.is_(True))
    if committee_type:
        stmt = stmt.where(Committee.committee_type == committee_type)
    stmt = stmt.order_by(Committee.name)

    result = await db.execute(stmt)
    committees = result.scalars().all()
    return [_serialize_committee(c) for c in committees]


@router.post("", response_model=CommitteeResponse, dependencies=[Depends(require_roles("SUPER_ADMIN", "REGIONAL_OFFICER"))])
async def create_committee(
    payload: CommitteeCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    existing = (await db.execute(select(Committee).where(Committee.code == payload.code))).scalar_one_or_none()
    if existing:
        raise ValidationError(f"Committee code '{payload.code}' already exists.")

    committee = Committee(
        code=payload.code,
        name=payload.name,
        committee_type=payload.committee_type,
        description=payload.description,
        quorum_required=payload.quorum_required,
        is_active=True,
        valid_from=payload.valid_from,
        valid_to=payload.valid_to,
    )
    db.add(committee)
    await db.commit()
    await db.refresh(committee)

    await record_audit_event(
        db=db,
        actor_id=current_user.id,
        action="COMMITTEE_CONSTITUTED",
        resource_type="Committee",
        resource_id=committee.id,
        details={"code": committee.code, "name": committee.name, "type": committee.committee_type},
    )

    return _serialize_committee(committee)


@router.get("/{id}", response_model=CommitteeResponse)
async def get_committee(
    id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    committee = await db.get(Committee, id)
    if not committee:
        raise NotFoundError("Committee", id)
    return _serialize_committee(committee)


@router.post("/{id}/members", response_model=CommitteeMembershipResponse, dependencies=[Depends(require_roles("SUPER_ADMIN", "REGIONAL_OFFICER"))])
async def add_committee_member(
    id: str,
    payload: CommitteeMemberCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    committee = await db.get(Committee, id)
    if not committee:
        raise NotFoundError("Committee", id)

    membership = CommitteeMembership(
        committee_id=committee.id,
        user_id=payload.user_id,
        expert_id=payload.expert_id,
        member_name=payload.member_name,
        member_role=payload.member_role,
        conflict_declarations_json=json.dumps(payload.conflict_declarations),
        is_active=True,
    )
    db.add(membership)
    await db.commit()
    await db.refresh(membership)

    await record_audit_event(
        db=db,
        actor_id=current_user.id,
        action="COMMITTEE_MEMBER_ADDED",
        resource_type="CommitteeMembership",
        resource_id=membership.id,
        details={"committee_code": committee.code, "member_name": payload.member_name, "role": payload.member_role},
    )

    return CommitteeMembershipResponse(
        id=membership.id,
        committee_id=membership.committee_id,
        user_id=membership.user_id,
        expert_id=membership.expert_id,
        member_name=membership.member_name,
        member_role=membership.member_role,
        conflict_declarations=payload.conflict_declarations,
        is_active=membership.is_active,
        created_at=membership.created_at,
    )
