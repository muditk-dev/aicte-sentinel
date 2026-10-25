import json
import hashlib
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.application import Application, ApplicationEvent
from app.models.decision import StatutoryDecision, DecisionCondition
from app.models.evc import EVCInspection, EVCReportVersion
from app.models.committee import HearingDocket, Hearing
from app.models.user import User
from app.core.exceptions import ValidationError, PermissionDeniedError, NotFoundError
from app.audit.service import record_audit_event
from app.schemas.decision import StatutoryDecisionIssueRequest, DecisionConditionCreate


class DecisionService:
    @staticmethod
    async def issue_statutory_decision(
        db: AsyncSession,
        request: StatutoryDecisionIssueRequest,
        actor: User,
        ip_address: Optional[str] = None,
    ) -> StatutoryDecision:
        # 1. Authority validation
        actor_roles = [r.code for r in actor.roles]
        if "SUPER_ADMIN" not in actor_roles and "REGIONAL_OFFICER" not in actor_roles:
            raise PermissionDeniedError(
                "Statutory decision authorization restricted to Regional Officers or Central Administrators."
            )

        # 2. Application lookup
        stmt = select(Application).where(Application.id == request.application_id)
        result = await db.execute(stmt)
        application = result.scalar_one_or_none()
        if not application:
            raise NotFoundError("Application", request.application_id)

        # 3. Immutability guard: Check if an active final decision already exists
        existing_stmt = select(StatutoryDecision).where(
            StatutoryDecision.application_id == application.id,
            StatutoryDecision.is_final.is_(True),
        )
        existing_dec = (await db.execute(existing_stmt)).scalar_one_or_none()
        if existing_dec:
            raise ValidationError(
                f"Statutory decision already finalized for application ({existing_dec.decision_number}). "
                "Final decisions are legally immutable and may only be reopened through formal Appellate Review."
            )

        # 4. Prerequisite application state validation
        allowed_decision_states = [
            "RECOMMENDED_APPROVAL",
            "STANDING_HEARING",
            "APPELLATE_REVIEW",
            "UNDER_SCRUTINY",
            "EVC_CONDUCTED",
        ]
        if application.current_status not in allowed_decision_states:
            raise ValidationError(
                f"Cannot issue final decision while application is in state '{application.current_status}'. "
                f"Must be one of {allowed_decision_states}."
            )

        # 5. Prerequisite: Inspection status check (if an inspection was scheduled)
        insp_stmt = select(EVCInspection).where(EVCInspection.application_id == application.id)
        inspections = (await db.execute(insp_stmt)).scalars().all()
        for insp in inspections:
            if insp.status != "CANCELLED":
                # Check for an ACCEPTED report version
                rep_stmt = (
                    select(EVCReportVersion)
                    .where(EVCReportVersion.inspection_id == insp.id)
                    .order_by(EVCReportVersion.version_number.desc())
                )
                rep = (await db.execute(rep_stmt)).scalars().first()
                if not rep or rep.review_status != "ACCEPTED":
                    raise ValidationError(
                        f"Inspection {insp.inspection_number} is pending satisfactory review. "
                        "An ACCEPTED EVC report is mandatory before rendering a final statutory decision."
                    )

        # 6. Prerequisite: Committee docket check (if a hearing docket was assigned)
        docket_stmt = select(HearingDocket).where(HearingDocket.application_id == application.id)
        dockets = (await db.execute(docket_stmt)).scalars().all()
        for docket in dockets:
            hearing = await db.get(Hearing, docket.hearing_id)
            if hearing and hearing.status not in ["RECOMMENDATION_RECORDED", "COMPLETED"]:
                raise ValidationError(
                    f"Hearing docket {docket.docket_number} remains pending. Committee hearing {hearing.hearing_number} "
                    f"is currently in '{hearing.status}' status and must record a recommendation before decision issuance."
                )

        # 7. Decision-specific requirements
        if request.decision_type == "CONDITIONALLY_APPROVED":
            if not request.conditions or len(request.conditions) == 0:
                raise ValidationError("Conditional approval requires at least one explicit compliance condition with a due date.")

        if request.decision_type == "REJECTED":
            if len(request.reasons.strip()) < 15:
                raise ValidationError("Statutory rejection requires detailed, auditable legal/regulatory reasons.")

        # 8. Non-repudiation SHA-256 attestation calculation
        now_iso = datetime.now(timezone.utc).isoformat()
        digest_input = (
            f"{application.id}:{request.decision_type}:{request.reasons.strip()}:"
            f"{actor.id}:{now_iso}:{request.governing_policy_version}:{request.declaration_attestation}"
        )
        sha256_attestation = hashlib.sha256(digest_input.encode("utf-8")).hexdigest()

        # Decision Number Generation
        timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d%H%M")
        decision_number = f"AICTE-DEC-{application.application_number}-{timestamp_str}"

        # 9. Create Statutory Decision Record
        authority_role = "SUPER_ADMIN" if "SUPER_ADMIN" in actor_roles else "REGIONAL_OFFICER"
        decision = StatutoryDecision(
            application_id=application.id,
            institution_id=application.institution_id,
            decision_number=decision_number,
            decision_type=request.decision_type,
            academic_year=application.academic_year,
            authority_role=authority_role,
            authorized_by_user_id=actor.id,
            authorized_at=now_iso,
            governing_policy_version=request.governing_policy_version,
            reasons=request.reasons,
            evidence_references_json=json.dumps(request.evidence_references),
            intake_approved=request.intake_approved,
            valid_for_years=request.valid_for_years,
            is_final=True,
            is_reconsidered=False,
            sha256_attestation=sha256_attestation,
            declaration_text=request.declaration_attestation,
        )
        db.add(decision)
        await db.flush()

        # Add Conditions if applicable
        for cond_in in request.conditions:
            cond = DecisionCondition(
                decision_id=decision.id,
                condition_code=cond_in.condition_code,
                description=cond_in.description,
                due_date=cond_in.due_date,
                compliance_status="PENDING",
            )
            db.add(cond)

        # 10. Transactional Application Workflow State Mutation
        old_status = application.current_status
        new_status = old_status
        if request.decision_type in ["APPROVED", "CONDITIONALLY_APPROVED"]:
            new_status = "APPROVED"
        elif request.decision_type == "REJECTED":
            new_status = "REJECTED"
        elif request.decision_type == "RETURNED_FOR_REVIEW":
            new_status = "UNDER_SCRUTINY"

        application.current_status = new_status

        app_event = ApplicationEvent(
            application_id=application.id,
            actor_id=actor.id,
            event_type="STATUTORY_DECISION",
            from_status=old_status,
            to_status=new_status,
            remarks=f"Statutory Decision rendered: {request.decision_type} ({decision_number})",
            event_payload_json=json.dumps({
                "decision_id": decision.id,
                "decision_number": decision_number,
                "decision_type": request.decision_type,
                "sha256_attestation": sha256_attestation,
            }),
        )
        db.add(app_event)

        # 11. Chained Audit Event
        await record_audit_event(
            db=db,
            actor_id=actor.id,
            action=f"STATUTORY_DECISION_{request.decision_type}",
            resource_type="StatutoryDecision",
            resource_id=decision.id,
            details={
                "application_id": application.id,
                "decision_number": decision_number,
                "decision_type": request.decision_type,
                "sha256_attestation": sha256_attestation,
                "intake_approved": request.intake_approved,
                "policy_version": request.governing_policy_version,
            },
            ip_address=ip_address,
        )

        await db.commit()
        await db.refresh(decision)
        return decision
