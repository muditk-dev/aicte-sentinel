import json
from typing import List, Optional
from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.core.exceptions import NotFoundError, PermissionDeniedError, ValidationError
from app.models.decision import StatutoryDecision, DecisionCondition
from app.models.application import Application, ApplicationEvent
from app.models.institution import Institution
from app.models.user import User
from app.security.dependencies import get_current_user, require_roles
from app.schemas.decision import (
    StatutoryDecisionIssueRequest,
    StatutoryDecisionResponse,
    DecisionConditionResponse,
    ReconsiderationRequest,
)
from app.services.decision_service import DecisionService
from app.audit.service import record_audit_event

router = APIRouter(prefix="/decisions", tags=["Authorized Statutory Decisions"])


async def _serialize_decision(db: AsyncSession, d: StatutoryDecision) -> StatutoryDecisionResponse:
    app = await db.get(Application, d.application_id)
    inst = await db.get(Institution, d.institution_id)
    officer = await db.get(User, d.authorized_by_user_id)

    # Conditions
    cond_stmt = select(DecisionCondition).where(DecisionCondition.decision_id == d.id)
    conditions = (await db.execute(cond_stmt)).scalars().all()
    cond_dtos = [
        DecisionConditionResponse(
            id=c.id,
            decision_id=c.decision_id,
            condition_code=c.condition_code,
            description=c.description,
            due_date=c.due_date,
            compliance_status=c.compliance_status,
            created_at=c.created_at,
        )
        for c in conditions
    ]

    ev_refs = []
    try:
        ev_refs = json.loads(d.evidence_references_json or "[]")
    except Exception:
        pass

    return StatutoryDecisionResponse(
        id=d.id,
        application_id=d.application_id,
        application_number=app.application_number if app else None,
        institution_id=d.institution_id,
        institution_name=inst.name if inst else None,
        decision_number=d.decision_number,
        decision_type=d.decision_type,
        academic_year=d.academic_year,
        authority_role=d.authority_role,
        authorized_by_user_id=d.authorized_by_user_id,
        authorized_by_name=officer.full_name if officer else None,
        authorized_at=d.authorized_at,
        governing_policy_version=d.governing_policy_version,
        reasons=d.reasons,
        evidence_references=ev_refs,
        intake_approved=d.intake_approved,
        valid_for_years=d.valid_for_years,
        is_final=d.is_final,
        is_reconsidered=d.is_reconsidered,
        reconsideration_reference=d.reconsideration_reference,
        sha256_attestation=d.sha256_attestation,
        declaration_text=d.declaration_text,
        conditions=cond_dtos,
        created_at=d.created_at,
    )


@router.get("", response_model=List[StatutoryDecisionResponse])
async def list_decisions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(StatutoryDecision)
    user_roles = [r.code for r in current_user.roles]
    if "INSTITUTION_ADMIN" in user_roles and current_user.institution_id:
        stmt = stmt.where(StatutoryDecision.institution_id == current_user.institution_id)

    stmt = stmt.order_by(StatutoryDecision.created_at.desc())
    result = await db.execute(stmt)
    decisions = result.scalars().all()

    return [await _serialize_decision(db, d) for d in decisions]


@router.get("/application/{application_id}", response_model=Optional[StatutoryDecisionResponse])
async def get_decision_by_application(
    application_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(StatutoryDecision).where(StatutoryDecision.application_id == application_id)
    d = (await db.execute(stmt)).scalar_one_or_none()
    if not d:
        return None

    user_roles = [r.code for r in current_user.roles]
    if "INSTITUTION_ADMIN" in user_roles and current_user.institution_id != d.institution_id:
        raise PermissionDeniedError("Unauthorized access to another institution's decision.")

    return await _serialize_decision(db, d)


@router.post("", response_model=StatutoryDecisionResponse, dependencies=[Depends(require_roles("SUPER_ADMIN", "REGIONAL_OFFICER"))])
async def issue_decision(
    payload: StatutoryDecisionIssueRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Issues a legally consequential statutory decision with non-repudiation cryptographic digest."""
    client_ip = request.client.host if request.client else None
    decision = await DecisionService.issue_statutory_decision(
        db=db,
        request=payload,
        actor=current_user,
        ip_address=client_ip,
    )
    return await _serialize_decision(db, decision)


@router.post("/{id}/reconsider", response_model=StatutoryDecisionResponse, dependencies=[Depends(require_roles("SUPER_ADMIN", "REGIONAL_OFFICER"))])
async def request_decision_reconsideration(
    id: str,
    payload: ReconsiderationRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Dockets a finalized decision for formal Standing Appellate Committee review."""
    decision = await db.get(StatutoryDecision, id)
    if not decision:
        raise NotFoundError("StatutoryDecision", id)

    if decision.decision_type not in ["REJECTED", "CONDITIONALLY_APPROVED"]:
        raise ValidationError("Only rejected or conditionally approved decisions are eligible for appellate reconsideration.")

    decision.is_reconsidered = True
    decision.reconsideration_reference = payload.appeal_petition_reference

    # Transition application state to APPELLATE_REVIEW
    app = await db.get(Application, decision.application_id)
    if app:
        old_status = app.current_status
        app.current_status = "APPELLATE_REVIEW"
        db.add(
            ApplicationEvent(
                application_id=app.id,
                actor_id=current_user.id,
                event_type="APPELLATE_PETITION_DOCKETED",
                from_status=old_status,
                to_status="APPELLATE_REVIEW",
                remarks=f"Appellate reconsideration docketed: {payload.appeal_petition_reference}",
                event_payload_json=json.dumps({"petition_ref": payload.appeal_petition_reference, "reason": payload.appeal_reason}),
            )
        )

    await db.commit()
    await db.refresh(decision)

    await record_audit_event(
        db=db,
        actor_id=current_user.id,
        action="DECISION_RECONSIDERATION_DOCKETED",
        resource_type="StatutoryDecision",
        resource_id=decision.id,
        details={
            "decision_number": decision.decision_number,
            "petition_ref": payload.appeal_petition_reference,
            "reason": payload.appeal_reason,
        },
    )

    return await _serialize_decision(db, decision)
