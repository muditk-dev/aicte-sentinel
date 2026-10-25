import json
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.exceptions import WorkflowTransitionError, PermissionDeniedError, NotFoundError
from app.models.application import Application, ApplicationEvent
from app.models.workflow import WorkflowVersion
from app.models.user import User
from app.audit.service import record_audit_event

# Default standard state machine definition
DEFAULT_STATE_MACHINE = {
    "DRAFT": {
        "allowed_targets": ["SUBMITTED"],
        "required_roles": ["INSTITUTION_ADMIN", "SUPER_ADMIN"],
    },
    "SUBMITTED": {
        "allowed_targets": ["UNDER_SCRUTINY"],
        "required_roles": ["SCRUTINY_OFFICER", "REGIONAL_OFFICER", "SUPER_ADMIN"],
    },
    "UNDER_SCRUTINY": {
        "allowed_targets": ["DEFICIENCY_ISSUED", "EVC_SCHEDULED", "RECOMMENDED_APPROVAL"],
        "required_roles": ["SCRUTINY_OFFICER", "REGIONAL_OFFICER", "SUPER_ADMIN"],
    },
    "DEFICIENCY_ISSUED": {
        "allowed_targets": ["RESUBMITTED"],
        "required_roles": ["INSTITUTION_ADMIN", "SUPER_ADMIN"],
    },
    "RESUBMITTED": {
        "allowed_targets": ["UNDER_SCRUTINY"],
        "required_roles": ["SCRUTINY_OFFICER", "REGIONAL_OFFICER", "SUPER_ADMIN"],
    },
    "EVC_SCHEDULED": {
        "allowed_targets": ["EVC_CONDUCTED"],
        "required_roles": ["EVC_EXPERT", "REGIONAL_OFFICER", "SUPER_ADMIN"],
    },
    "EVC_CONDUCTED": {
        "allowed_targets": ["RECOMMENDED_APPROVAL", "STANDING_HEARING"],
        "required_roles": ["EVC_EXPERT", "REGIONAL_OFFICER", "SUPER_ADMIN"],
    },
    "STANDING_HEARING": {
        "allowed_targets": ["RECOMMENDED_APPROVAL", "REJECTED"],
        "required_roles": ["REGIONAL_OFFICER", "SUPER_ADMIN"],
    },
    "RECOMMENDED_APPROVAL": {
        "allowed_targets": ["APPROVED", "REJECTED"],
        "required_roles": ["REGIONAL_OFFICER", "SUPER_ADMIN"],
    },
    "APPROVED": {
        "allowed_targets": [],
        "required_roles": [],
    },
    "REJECTED": {
        "allowed_targets": ["APPELLATE_REVIEW"],
        "required_roles": ["REGIONAL_OFFICER", "SUPER_ADMIN"],
    },
    "APPELLATE_REVIEW": {
        "allowed_targets": ["APPROVED", "REJECTED"],
        "required_roles": ["SUPER_ADMIN"],
    },
}


class WorkflowEngine:
    @staticmethod
    async def transition(
        db: AsyncSession,
        application_id: str,
        target_status: str,
        actor: User,
        remarks: str,
        metadata: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
    ) -> Application:
        stmt = select(Application).where(Application.id == application_id)
        result = await db.execute(stmt)
        app = result.scalar_one_or_none()
        if not app:
            raise NotFoundError("Application", application_id)

        current_status = app.current_status

        # Retrieve version state machine rules
        version_stmt = select(WorkflowVersion).where(WorkflowVersion.id == app.version_id)
        version_result = await db.execute(version_stmt)
        version = version_result.scalar_one_or_none()

        sm_rules = DEFAULT_STATE_MACHINE
        if version and version.state_machine_json:
            try:
                sm_rules = json.loads(version.state_machine_json)
            except Exception:
                sm_rules = DEFAULT_STATE_MACHINE

        # 1. Guard: Check if source state has configured transitions
        state_config = sm_rules.get(current_status)
        if not state_config:
            raise WorkflowTransitionError(
                current_status, target_status, f"Current state '{current_status}' is terminal or unconfigured."
            )

        allowed_targets = state_config.get("allowed_targets", [])
        if target_status not in allowed_targets:
            raise WorkflowTransitionError(
                current_status,
                target_status,
                f"Transition not allowed by APH state machine. Allowed targets from '{current_status}': {allowed_targets}",
            )

        # 2. Guard: Check actor role authorization
        required_roles = state_config.get("required_roles", [])
        actor_roles = [r.code for r in actor.roles]
        if "SUPER_ADMIN" not in actor_roles and not any(r in actor_roles for r in required_roles):
            raise PermissionDeniedError(
                f"User lacks required statutory authority for this transition. Required: {required_roles}"
            )

        # 3. Apply state mutation
        app.current_status = target_status

        # 4. Record application event
        event = ApplicationEvent(
            application_id=app.id,
            actor_id=actor.id,
            event_type="STATE_TRANSITION",
            from_status=current_status,
            to_status=target_status,
            remarks=remarks,
            event_payload_json=json.dumps(metadata or {}),
        )
        db.add(event)

        # 5. Record cryptographically chained audit record
        await record_audit_event(
            db=db,
            actor_id=actor.id,
            action=f"TRANSITION_TO_{target_status}",
            resource_type="Application",
            resource_id=app.id,
            details={
                "from_status": current_status,
                "to_status": target_status,
                "remarks": remarks,
                "metadata": metadata or {},
            },
            ip_address=ip_address,
        )

        await db.commit()
        await db.refresh(app)
        return app
