from typing import List
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from app.core.database import get_db
from app.models.audit import AuditEvent
from app.models.user import User
from app.schemas.audit import AuditEventResponse, AuditVerificationResponse
from app.security.dependencies import get_current_user, require_roles
from app.audit.service import verify_audit_chain

router = APIRouter(prefix="/audit", tags=["Tamper-Evident Audit Ledger"])


@router.get("/events", response_model=List[AuditEventResponse])
async def list_audit_events(
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles("SUPER_ADMIN", "REGIONAL_OFFICER")),
):
    """Retrieve chronological audit trail with SHA-256 integrity hashes."""
    stmt = select(AuditEvent).order_by(desc(AuditEvent.sequence_number)).limit(limit).offset(offset)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/verify", response_model=AuditVerificationResponse)
async def verify_ledger(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Publicly verifiable cryptographic chain check.
    Traverses the hash chain from Genesis and validates zero tamper across all entries.
    """
    return await verify_audit_chain(db)
