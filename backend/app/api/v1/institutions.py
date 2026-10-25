from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.core.exceptions import NotFoundError, ConflictError
from app.models.institution import Institution
from app.models.user import User
from app.schemas.institution import InstitutionCreate, InstitutionResponse
from app.security.dependencies import get_current_user, require_roles
from app.audit.service import record_audit_event

router = APIRouter(prefix="/institutions", tags=["Institutions Registry"])


@router.get("", response_model=List[InstitutionResponse])
async def list_institutions(
    region: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List institutions matching filters with tenant restrictions where appropriate."""
    stmt = select(Institution)

    # If applicant/institution admin, restrict to their own institution
    user_roles = [r.code for r in current_user.roles]
    if "INSTITUTION_ADMIN" in user_roles and "SUPER_ADMIN" not in user_roles:
        stmt = stmt.where(Institution.id == current_user.institution_id)
    else:
        if region:
            stmt = stmt.where(Institution.region == region)
        if state:
            stmt = stmt.where(Institution.state == state)
        if status_filter:
            stmt = stmt.where(Institution.status == status_filter)

    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("", response_model=InstitutionResponse, status_code=status.HTTP_201_CREATED)
async def create_institution(
    payload: InstitutionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles("SUPER_ADMIN", "REGIONAL_OFFICER")),
):
    """Register a technical institution in AICTE Sentinel."""
    # Check duplicate code
    stmt = select(Institution).where(Institution.code == payload.code)
    existing = await db.execute(stmt)
    if existing.scalar_one_or_none():
        raise ConflictError(f"Institution with code '{payload.code}' already exists.")

    inst = Institution(**payload.model_dump())
    db.add(inst)
    await db.flush()

    await record_audit_event(
        db=db,
        actor_id=current_user.id,
        action="CREATE_INSTITUTION",
        resource_type="Institution",
        resource_id=inst.id,
        details=payload.model_dump(),
    )
    await db.commit()
    await db.refresh(inst)
    return inst


@router.get("/{institution_id}", response_model=InstitutionResponse)
async def get_institution(
    institution_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get institution profile by ID."""
    stmt = select(Institution).where(Institution.id == institution_id)
    result = await db.execute(stmt)
    inst = result.scalar_one_or_none()
    if not inst:
        raise NotFoundError("Institution", institution_id)
    return inst
