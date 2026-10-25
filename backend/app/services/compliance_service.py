import csv
import io
import json
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy import select, and_, or_, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    NotFoundError,
    PermissionDeniedError,
    ValidationError,
    SentinelException,
)
from app.models.compliance import (
    ComplianceObligation,
    ObligationEvidence,
    ObligationReviewHistory,
    ComplianceEscalation,
)
from app.models.institution import Institution
from app.models.application import Application
from app.models.decision import StatutoryDecision
from app.models.document import Document
from app.models.user import User
from app.models.deficiency import Notification
from app.audit.service import record_audit_event
from app.schemas.compliance import (
    ObligationCreateRequest,
    ObligationUpdateRequest,
    EvidenceSubmitRequest,
    OfficerReviewRequest,
    ComplianceObligationResponse,
    ObligationEvidenceResponse,
    ObligationReviewHistoryResponse,
    ComplianceEscalationResponse,
    ComplianceSummaryReportResponse,
    CategoryBreakdownItem,
    InstitutionComplianceReportItem,
    ComplianceDeadlineItemResponse,
    ComplianceDeficiencyReportItem,
)

logger = logging.getLogger("sentinel.compliance_service")

# Permitted state transitions
VALID_TRANSITIONS: Dict[str, List[str]] = {
    "PENDING": ["SUBMITTED", "OVERDUE", "CLOSED"],
    "SUBMITTED": ["UNDER_REVIEW", "OVERDUE", "CLOSED"],
    "UNDER_REVIEW": ["COMPLIANT", "DEFICIENT", "OVERDUE", "CLOSED"],
    "DEFICIENT": ["SUBMITTED", "OVERDUE", "CLOSED"],
    "OVERDUE": ["SUBMITTED", "CLOSED"],
    "COMPLIANT": ["CLOSED"],
    "CLOSED": [],  # Terminal state
}

# Dangerous leading characters for spreadsheet formula injection (OWASP guideline)
FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def sanitize_csv_cell(value: Any) -> str:
    """
    Sanitizes string values to prevent Spreadsheet Formula Injection (CSV Injection).
    Prepends a single quote (') if the cell starts with =, +, -, @, tab, or carriage return.
    """
    if value is None:
        return ""
    str_val = str(value)
    if str_val.startswith(FORMULA_PREFIXES):
        return f"'{str_val}"
    return str_val.strip()


def ensure_utc(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


class ComplianceService:
    """
    Post-Approval Obligations and Compliance Monitoring Service.
    Enforces RBAC, tenant isolation, validated state machine transitions,
    tamper-evident audit logging, and formula-injection-safe reporting.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    # --------------------------------------------------------------------------
    # SERIALIZATION HELPERS
    # --------------------------------------------------------------------------

    def serialize_obligation(self, ob: ComplianceObligation) -> ComplianceObligationResponse:
        inst_name = ob.institution.name if ob.institution else None
        officer_name = ob.assigned_officer.full_name if ob.assigned_officer else None

        evidences = [
            ObligationEvidenceResponse(
                id=e.id,
                obligation_id=e.obligation_id,
                document_id=e.document_id,
                title=e.title,
                description=e.description,
                file_url=e.file_url,
                sha256_hash=e.sha256_hash,
                uploaded_by_user_id=e.uploaded_by_user_id,
                submission_notes=e.submission_notes,
                created_at=ensure_utc(e.created_at),
            )
            for e in (ob.evidences or [])
        ]

        history = [
            ObligationReviewHistoryResponse(
                id=h.id,
                obligation_id=h.obligation_id,
                actor_id=h.actor_id,
                actor_role=h.actor_role,
                action=h.action,
                previous_status=h.previous_status,
                new_status=h.new_status,
                comments=h.comments,
                created_at=ensure_utc(h.created_at),
            )
            for h in (ob.history or [])
        ]

        return ComplianceObligationResponse(
            id=ob.id,
            obligation_code=ob.obligation_code,
            institution_id=ob.institution_id,
            institution_name=inst_name,
            application_id=ob.application_id,
            decision_id=ob.decision_id,
            title=ob.title,
            description=ob.description,
            category=ob.category,
            source_reference=ob.source_reference,
            applicability=ob.applicability,
            assigned_officer_id=ob.assigned_officer_id,
            assigned_officer_name=officer_name,
            issue_date=ensure_utc(ob.issue_date),
            due_date=ensure_utc(ob.due_date),
            recurrence=ob.recurrence,
            status=ob.status,
            is_synthetic_demonstration=ob.is_synthetic_demonstration,
            is_automated_advisory=ob.is_automated_advisory,
            closed_at=ensure_utc(ob.closed_at),
            closed_by_user_id=ob.closed_by_user_id,
            created_at=ensure_utc(ob.created_at),
            updated_at=ensure_utc(ob.updated_at),
            evidences=evidences,
            history=history,
        )

    # --------------------------------------------------------------------------
    # OBLIGATION MANAGEMENT (M14)
    # --------------------------------------------------------------------------

    async def create_obligation(
        self,
        payload: ObligationCreateRequest,
        actor: User,
    ) -> ComplianceObligationResponse:
        """
        Creates a new post-approval compliance obligation.
        Authorized roles: SCRUTINY_OFFICER, REGIONAL_OFFICER, SUPER_ADMIN.
        """
        # Validate institution existence
        inst_stmt = select(Institution).where(Institution.id == payload.institution_id)
        inst_res = await self.db.execute(inst_stmt)
        inst = inst_res.scalar_one_or_none()
        if not inst:
            raise NotFoundError("Institution", payload.institution_id)

        # Ensure due_date > issue_date
        issue_dt = ensure_utc(payload.issue_date)
        due_dt = ensure_utc(payload.due_date)
        if due_dt <= issue_dt:
            raise ValidationError("due_date must be strictly after issue_date", details={"field": "due_date"})

        # Generate unique obligation code
        now_year = datetime.now(timezone.utc).year
        cat_prefix = payload.category[:4].upper()
        # Count existing obligations to generate sequential code
        count_stmt = select(func.count(ComplianceObligation.id))
        count_res = await self.db.execute(count_stmt)
        seq_num = (count_res.scalar() or 0) + 1
        code = f"OBL-{now_year}-{cat_prefix}-{seq_num:04d}"

        initial_status = "PENDING"

        obligation = ComplianceObligation(
            obligation_code=code,
            institution_id=payload.institution_id,
            application_id=payload.application_id,
            decision_id=payload.decision_id,
            title=payload.title,
            description=payload.description,
            category=payload.category,
            source_reference=payload.source_reference,
            applicability=payload.applicability,
            assigned_officer_id=payload.assigned_officer_id,
            issue_date=issue_dt,
            due_date=due_dt,
            recurrence=payload.recurrence,
            status=initial_status,
            is_synthetic_demonstration=payload.is_synthetic_demonstration,
            is_automated_advisory=False,
        )
        self.db.add(obligation)
        await self.db.flush()

        # Add history record
        actor_role = actor.roles[0].code if actor.roles else "OFFICER"
        history = ObligationReviewHistory(
            obligation_id=obligation.id,
            actor_id=actor.id,
            actor_role=actor_role,
            action="CREATED",
            previous_status="NONE",
            new_status=initial_status,
            comments=f"Compliance obligation issued under {payload.source_reference}.",
        )
        self.db.add(history)
        await self.db.commit()
        await self.db.refresh(obligation)

        # Chained SHA-256 audit record
        await record_audit_event(
            db=self.db,
            actor_id=actor.id,
            action="COMPLIANCE_OBLIGATION_CREATED",
            resource_type="COMPLIANCE_OBLIGATION",
            resource_id=obligation.id,
            details={
                "obligation_code": obligation.obligation_code,
                "institution_id": obligation.institution_id,
                "title": obligation.title,
                "category": obligation.category,
                "due_date": obligation.due_date.isoformat(),
                "source_reference": obligation.source_reference,
            },
        )

        return self.serialize_obligation(obligation)

    async def list_obligations(
        self,
        current_user: User,
        category: Optional[str] = None,
        status: Optional[str] = None,
        institution_id: Optional[str] = None,
        search: Optional[str] = None,
        overdue_only: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[ComplianceObligationResponse], int]:
        """
        Lists obligations with tenant isolation and filtering.
        """
        user_roles = [r.code for r in current_user.roles]
        stmt = select(ComplianceObligation)
        count_stmt = select(func.count(ComplianceObligation.id))

        conditions = []

        # Tenant isolation
        if "INSTITUTION_USER" in user_roles or "INSTITUTION_ADMIN" in user_roles:
            conditions.append(ComplianceObligation.institution_id == current_user.institution_id)
        elif institution_id:
            conditions.append(ComplianceObligation.institution_id == institution_id)

        if category:
            conditions.append(ComplianceObligation.category == category)
        if status:
            conditions.append(ComplianceObligation.status == status)
        if overdue_only:
            conditions.append(ComplianceObligation.status == "OVERDUE")
        if search:
            search_pat = f"%{search}%"
            conditions.append(
                or_(
                    ComplianceObligation.title.ilike(search_pat),
                    ComplianceObligation.obligation_code.ilike(search_pat),
                    ComplianceObligation.source_reference.ilike(search_pat),
                )
            )

        if conditions:
            stmt = stmt.where(and_(*conditions))
            count_stmt = count_stmt.where(and_(*conditions))

        # Order by due date ascending
        stmt = stmt.order_by(ComplianceObligation.due_date.asc(), ComplianceObligation.created_at.desc())
        stmt = stmt.limit(limit).offset(offset)

        total_res = await self.db.execute(count_stmt)
        total = total_res.scalar() or 0

        res = await self.db.execute(stmt)
        obligations = res.scalars().all()

        return [self.serialize_obligation(ob) for ob in obligations], total

    async def get_obligation(
        self,
        obligation_id: str,
        current_user: User,
    ) -> ComplianceObligationResponse:
        """
        Fetches single obligation with tenant check.
        """
        stmt = select(ComplianceObligation).where(ComplianceObligation.id == obligation_id)
        res = await self.db.execute(stmt)
        obligation = res.scalar_one_or_none()
        if not obligation:
            raise NotFoundError("ComplianceObligation", obligation_id)

        # Tenant check
        user_roles = [r.code for r in current_user.roles]
        if "INSTITUTION_USER" in user_roles or "INSTITUTION_ADMIN" in user_roles:
            if obligation.institution_id != current_user.institution_id:
                raise PermissionDeniedError("Cannot inspect compliance obligations of another institution.")

        return self.serialize_obligation(obligation)

    async def update_obligation(
        self,
        obligation_id: str,
        payload: ObligationUpdateRequest,
        actor: User,
    ) -> ComplianceObligationResponse:
        """
        Updates configurable obligation properties. Officer/Admin only.
        """
        stmt = select(ComplianceObligation).where(ComplianceObligation.id == obligation_id)
        res = await self.db.execute(stmt)
        ob = res.scalar_one_or_none()
        if not ob:
            raise NotFoundError("ComplianceObligation", obligation_id)

        if ob.status == "CLOSED":
            raise SentinelException("Closed obligations cannot be edited.", code="OBLIGATION_CLOSED", status_code=400)

        changes: Dict[str, Any] = {}
        if payload.title is not None:
            ob.title = payload.title
            changes["title"] = payload.title
        if payload.description is not None:
            ob.description = payload.description
        if payload.category is not None:
            ob.category = payload.category
            changes["category"] = payload.category
        if payload.source_reference is not None:
            ob.source_reference = payload.source_reference
            changes["source_reference"] = payload.source_reference
        if payload.applicability is not None:
            ob.applicability = payload.applicability
        if payload.assigned_officer_id is not None:
            ob.assigned_officer_id = payload.assigned_officer_id
            changes["assigned_officer_id"] = payload.assigned_officer_id
        if payload.due_date is not None:
            new_due = ensure_utc(payload.due_date)
            if new_due <= ob.issue_date:
                raise ValidationError("due_date must be strictly after issue_date", details={"field": "due_date"})
            ob.due_date = new_due
            changes["due_date"] = new_due.isoformat()
        if payload.recurrence is not None:
            ob.recurrence = payload.recurrence
            changes["recurrence"] = payload.recurrence

        await self.db.commit()
        await self.db.refresh(ob)

        await record_audit_event(
            db=self.db,
            actor_id=actor.id,
            action="COMPLIANCE_OBLIGATION_UPDATED",
            resource_type="COMPLIANCE_OBLIGATION",
            resource_id=ob.id,
            details=changes,
        )

        return self.serialize_obligation(ob)

    async def submit_evidence(
        self,
        obligation_id: str,
        payload: EvidenceSubmitRequest,
        actor: User,
    ) -> ComplianceObligationResponse:
        """
        Institution submits curative or recurring compliance evidence.
        Transitions status from PENDING, DEFICIENT, or OVERDUE to SUBMITTED.
        """
        stmt = select(ComplianceObligation).where(ComplianceObligation.id == obligation_id)
        res = await self.db.execute(stmt)
        ob = res.scalar_one_or_none()
        if not ob:
            raise NotFoundError("ComplianceObligation", obligation_id)

        user_roles = [r.code for r in actor.roles]
        if "INSTITUTION_USER" in user_roles or "INSTITUTION_ADMIN" in user_roles:
            if ob.institution_id != actor.institution_id:
                raise PermissionDeniedError("Cannot submit evidence for another institution's obligation.")

        if ob.status == "CLOSED":
            raise SentinelException("Cannot submit evidence for a closed obligation.", code="OBLIGATION_CLOSED", status_code=400)

        # Create evidence record
        evidence = ObligationEvidence(
            obligation_id=ob.id,
            document_id=payload.document_id,
            title=payload.title,
            description=payload.description,
            file_url=payload.file_url,
            sha256_hash=payload.sha256_hash,
            uploaded_by_user_id=actor.id,
            submission_notes=payload.submission_notes,
        )
        self.db.add(evidence)

        # Transition status to SUBMITTED
        prev_status = ob.status
        ob.status = "SUBMITTED"

        actor_role = actor.roles[0].code if actor.roles else "INSTITUTION_USER"
        history = ObligationReviewHistory(
            obligation_id=ob.id,
            actor_id=actor.id,
            actor_role=actor_role,
            action="EVIDENCE_SUBMITTED",
            previous_status=prev_status,
            new_status="SUBMITTED",
            comments=payload.submission_notes or f"Evidence uploaded: {payload.title}",
        )
        self.db.add(history)
        await self.db.commit()
        await self.db.refresh(ob)

        await record_audit_event(
            db=self.db,
            actor_id=actor.id,
            action="COMPLIANCE_EVIDENCE_SUBMITTED",
            resource_type="COMPLIANCE_OBLIGATION",
            resource_id=ob.id,
            details={
                "evidence_title": payload.title,
                "document_id": payload.document_id,
                "previous_status": prev_status,
                "new_status": "SUBMITTED",
            },
        )

        return self.serialize_obligation(ob)

    async def officer_review(
        self,
        obligation_id: str,
        payload: OfficerReviewRequest,
        actor: User,
    ) -> ComplianceObligationResponse:
        """
        Officer reviews evidence and determines outcome:
        - VERIFIED_COMPLIANT -> COMPLIANT
        - DEFICIENCY_FLAGGED -> DEFICIENT (with optional cure deadline extension)
        - CLOSED -> CLOSED
        """
        stmt = select(ComplianceObligation).where(ComplianceObligation.id == obligation_id)
        res = await self.db.execute(stmt)
        ob = res.scalar_one_or_none()
        if not ob:
            raise NotFoundError("ComplianceObligation", obligation_id)

        if ob.status == "CLOSED":
            raise SentinelException("Obligation is already closed.", code="OBLIGATION_CLOSED", status_code=400)

        prev_status = ob.status
        action = payload.decision

        if payload.decision == "VERIFIED_COMPLIANT":
            ob.status = "COMPLIANT"
            notif_title = f"Compliance Verified: {ob.title}"
            notif_msg = f"Your submission for obligation {ob.obligation_code} has been reviewed and verified compliant. Remarks: {payload.review_comments}"
        elif payload.decision == "DEFICIENCY_FLAGGED":
            ob.status = "DEFICIENT"
            if payload.deficiency_cure_days and payload.deficiency_cure_days > 0:
                ob.due_date = datetime.now(timezone.utc) + timedelta(days=payload.deficiency_cure_days)
            notif_title = f"Deficiency Flagged: {ob.title}"
            notif_msg = f"Obligation {ob.obligation_code} has been marked DEFICIENT upon scrutiny. Reason: {payload.review_comments}. Please upload curative documentation by {ob.due_date.strftime('%d-%b-%Y')}."
        elif payload.decision == "CLOSED":
            ob.status = "CLOSED"
            ob.closed_at = datetime.now(timezone.utc)
            ob.closed_by_user_id = actor.id
            notif_title = f"Compliance Obligation Closed: {ob.title}"
            notif_msg = f"Obligation {ob.obligation_code} has been formally closed by the regulatory desk. Remarks: {payload.review_comments}"
        else:
            raise ValidationError(
                f"Invalid review decision '{payload.decision}'. Allowed: VERIFIED_COMPLIANT, DEFICIENCY_FLAGGED, CLOSED",
                details={"field": "decision"},
            )

        actor_role = actor.roles[0].code if actor.roles else "OFFICER"
        history = ObligationReviewHistory(
            obligation_id=ob.id,
            actor_id=actor.id,
            actor_role=actor_role,
            action=action,
            previous_status=prev_status,
            new_status=ob.status,
            comments=payload.review_comments,
        )
        self.db.add(history)

        # In-app notification to the institution
        notif = Notification(
            institution_id=ob.institution_id,
            title=notif_title,
            message=notif_msg,
            category="COMPLIANCE_REVIEW",
            link_url=f"/compliance/obligations/{ob.id}",
            is_read=False,
            delivery_status="IN_APP_DELIVERED",
        )
        self.db.add(notif)

        await self.db.commit()
        await self.db.refresh(ob)

        await record_audit_event(
            db=self.db,
            actor_id=actor.id,
            action=f"COMPLIANCE_OFFICER_REVIEW_{action}",
            resource_type="COMPLIANCE_OBLIGATION",
            resource_id=ob.id,
            details={
                "previous_status": prev_status,
                "new_status": ob.status,
                "decision": payload.decision,
                "review_comments": payload.review_comments,
            },
        )

        return self.serialize_obligation(ob)

    async def transition_status(
        self,
        obligation_id: str,
        target_status: str,
        comments: Optional[str],
        actor: User,
    ) -> ComplianceObligationResponse:
        """
        Generic state machine transition with transition validity guards.
        """
        stmt = select(ComplianceObligation).where(ComplianceObligation.id == obligation_id)
        res = await self.db.execute(stmt)
        ob = res.scalar_one_or_none()
        if not ob:
            raise NotFoundError("ComplianceObligation", obligation_id)

        user_roles = [r.code for r in actor.roles]
        is_inst_user = "INSTITUTION_USER" in user_roles or "INSTITUTION_ADMIN" in user_roles

        if is_inst_user and ob.institution_id != actor.institution_id:
            raise PermissionDeniedError("Cannot transition another institution's obligation.")

        current_st = ob.status
        allowed = VALID_TRANSITIONS.get(current_st, [])
        if target_status not in allowed:
            raise SentinelException(
                f"Invalid state transition from '{current_st}' to '{target_status}'. Allowed: {', '.join(allowed) or 'None (terminal)'}",
                code="INVALID_STATE_TRANSITION",
                status_code=400,
            )

        # Institutional users can only transition to SUBMITTED
        if is_inst_user and target_status not in ("SUBMITTED",):
            raise PermissionDeniedError("Institutions may only submit evidence to transition obligations.")

        ob.status = target_status
        if target_status == "CLOSED":
            ob.closed_at = datetime.now(timezone.utc)
            ob.closed_by_user_id = actor.id

        actor_role = actor.roles[0].code if actor.roles else "USER"
        history = ObligationReviewHistory(
            obligation_id=ob.id,
            actor_id=actor.id,
            actor_role=actor_role,
            action=f"TRANSITION_TO_{target_status}",
            previous_status=current_st,
            new_status=target_status,
            comments=comments or f"Status transitioned to {target_status}",
        )
        self.db.add(history)
        await self.db.commit()
        await self.db.refresh(ob)

        await record_audit_event(
            db=self.db,
            actor_id=actor.id,
            action="COMPLIANCE_STATUS_TRANSITION",
            resource_type="COMPLIANCE_OBLIGATION",
            resource_id=ob.id,
            details={
                "previous_status": current_st,
                "new_status": target_status,
                "comments": comments,
            },
        )

        return self.serialize_obligation(ob)

    # --------------------------------------------------------------------------
    # COMPLIANCE REPORTS & CSV EXPORT (M16)
    # --------------------------------------------------------------------------

    async def get_summary_report(self, current_user: User) -> ComplianceSummaryReportResponse:
        """
        Summary KPI metrics across obligations.
        """
        user_roles = [r.code for r in current_user.roles]
        filter_inst = current_user.institution_id if ("INSTITUTION_USER" in user_roles or "INSTITUTION_ADMIN" in user_roles) else None

        base_stmt = select(ComplianceObligation)
        if filter_inst:
            base_stmt = base_stmt.where(ComplianceObligation.institution_id == filter_inst)

        res = await self.db.execute(base_stmt)
        all_obs = res.scalars().all()

        total = len(all_obs)
        compliant = sum(1 for o in all_obs if o.status == "COMPLIANT")
        pending = sum(1 for o in all_obs if o.status == "PENDING")
        under_review = sum(1 for o in all_obs if o.status == "UNDER_REVIEW")
        deficient = sum(1 for o in all_obs if o.status == "DEFICIENT")
        overdue = sum(1 for o in all_obs if o.status == "OVERDUE")
        closed = sum(1 for o in all_obs if o.status == "CLOSED")

        rate = round((compliant / max(1, (total - closed))) * 100.0, 1) if (total - closed) > 0 else 100.0

        # Category Breakdown
        categories: Dict[str, Dict[str, int]] = {}
        for o in all_obs:
            c = o.category
            if c not in categories:
                categories[c] = {"total": 0, "compliant": 0, "pending": 0, "deficient": 0, "overdue": 0}
            categories[c]["total"] += 1
            if o.status == "COMPLIANT":
                categories[c]["compliant"] += 1
            elif o.status in ("PENDING", "SUBMITTED", "UNDER_REVIEW"):
                categories[c]["pending"] += 1
            elif o.status == "DEFICIENT":
                categories[c]["deficient"] += 1
            elif o.status == "OVERDUE":
                categories[c]["overdue"] += 1

        cat_items = [
            CategoryBreakdownItem(
                category=cat,
                total=data["total"],
                compliant=data["compliant"],
                pending=data["pending"],
                deficient=data["deficient"],
                overdue=data["overdue"],
            )
            for cat, data in sorted(categories.items())
        ]

        # Active escalations
        esc_stmt = select(func.count(ComplianceEscalation.id)).where(ComplianceEscalation.is_resolved == False)
        if filter_inst:
            esc_stmt = esc_stmt.where(ComplianceEscalation.institution_id == filter_inst)
        esc_res = await self.db.execute(esc_stmt)
        active_esc = esc_res.scalar() or 0

        return ComplianceSummaryReportResponse(
            total_obligations=total,
            total_compliant=compliant,
            total_pending=pending,
            total_under_review=under_review,
            total_deficient=deficient,
            total_overdue=overdue,
            total_closed=closed,
            compliance_rate_percent=rate,
            categories_breakdown=cat_items,
            active_escalations_count=active_esc,
            is_synthetic_demonstration=True,
        )

    async def get_institution_reports(
        self,
        current_user: User,
        region: Optional[str] = None,
    ) -> List[InstitutionComplianceReportItem]:
        """
        Compliance rating breakdown by institution.
        """
        user_roles = [r.code for r in current_user.roles]
        is_inst_user = "INSTITUTION_USER" in user_roles or "INSTITUTION_ADMIN" in user_roles

        inst_stmt = select(Institution)
        if is_inst_user:
            inst_stmt = inst_stmt.where(Institution.id == current_user.institution_id)
        elif region:
            inst_stmt = inst_stmt.where(Institution.region == region)

        inst_res = await self.db.execute(inst_stmt)
        institutions = inst_res.scalars().all()

        results: List[InstitutionComplianceReportItem] = []
        for inst in institutions:
            ob_stmt = select(ComplianceObligation).where(ComplianceObligation.institution_id == inst.id)
            ob_res = await self.db.execute(ob_stmt)
            obs = ob_res.scalars().all()

            total = len(obs)
            comp = sum(1 for o in obs if o.status == "COMPLIANT")
            pending = sum(1 for o in obs if o.status in ("PENDING", "SUBMITTED", "UNDER_REVIEW"))
            overdue = sum(1 for o in obs if o.status == "OVERDUE")
            deficient = sum(1 for o in obs if o.status == "DEFICIENT")
            pct = round((comp / max(1, total)) * 100.0, 1) if total > 0 else 100.0

            results.append(
                InstitutionComplianceReportItem(
                    institution_id=inst.id,
                    institution_name=inst.name,
                    institution_code=inst.code,
                    region=inst.region,
                    state=inst.state,
                    total_obligations=total,
                    compliant_count=comp,
                    pending_count=pending,
                    overdue_count=overdue,
                    deficient_count=deficient,
                    compliance_percentage=pct,
                    is_fully_compliant=(overdue == 0 and deficient == 0 and comp > 0),
                )
            )

        results.sort(key=lambda x: x.compliance_percentage, reverse=True)
        return results

    async def get_deadlines_report(
        self,
        current_user: User,
        days_ahead: int = 60,
    ) -> List[ComplianceDeadlineItemResponse]:
        """
        Upcoming deadlines and overdue items across obligations, certificates, and approval renewals.
        """
        user_roles = [r.code for r in current_user.roles]
        filter_inst = current_user.institution_id if ("INSTITUTION_USER" in user_roles or "INSTITUTION_ADMIN" in user_roles) else None

        now = datetime.now(timezone.utc)
        horizon = now + timedelta(days=days_ahead)

        # 1. Post-Approval Obligations
        stmt = select(ComplianceObligation).where(
            ComplianceObligation.status.notin_(["COMPLIANT", "CLOSED"])
        )
        if filter_inst:
            stmt = stmt.where(ComplianceObligation.institution_id == filter_inst)
        res = await self.db.execute(stmt)
        obligations = res.scalars().all()

        items: List[ComplianceDeadlineItemResponse] = []
        for ob in obligations:
            due_dt = ensure_utc(ob.due_date)
            diff_days = int((due_dt - now).total_seconds() // 86400)

            if diff_days < 0:
                urgency = "OVERDUE"
            elif diff_days == 0:
                urgency = "DUE_TODAY"
            elif diff_days <= 7:
                urgency = "CRITICAL_7_DAYS"
            elif diff_days <= 30:
                urgency = "APPROACHING_30_DAYS"
            else:
                urgency = "HEALTHY"

            items.append(
                ComplianceDeadlineItemResponse(
                    id=ob.id,
                    item_type="OBLIGATION",
                    title=ob.title,
                    institution_id=ob.institution_id,
                    institution_name=ob.institution.name if ob.institution else "Unknown",
                    due_date=due_dt,
                    days_remaining=diff_days,
                    urgency_status=urgency,
                    category=ob.category,
                    reference_code=ob.obligation_code,
                )
            )

        # Sort: Overdue & urgent first
        items.sort(key=lambda x: x.days_remaining)
        return items

    async def get_deficiencies_report(
        self,
        current_user: User,
    ) -> List[ComplianceDeficiencyReportItem]:
        """
        Review queue of outstanding deficiencies and overdue obligations.
        """
        user_roles = [r.code for r in current_user.roles]
        filter_inst = current_user.institution_id if ("INSTITUTION_USER" in user_roles or "INSTITUTION_ADMIN" in user_roles) else None

        stmt = select(ComplianceObligation).where(
            ComplianceObligation.status.in_(["DEFICIENT", "OVERDUE"])
        )
        if filter_inst:
            stmt = stmt.where(ComplianceObligation.institution_id == filter_inst)
        res = await self.db.execute(stmt)
        obs = res.scalars().all()

        now = datetime.now(timezone.utc)
        items: List[ComplianceDeficiencyReportItem] = []
        for ob in obs:
            due_dt = ensure_utc(ob.due_date)
            diff_days = max(0, int((now - due_dt).total_seconds() // 86400))
            
            # Find last review comment
            last_comment = None
            if ob.history:
                for h in reversed(ob.history):
                    if h.comments:
                        last_comment = h.comments
                        break

            officer_name = ob.assigned_officer.full_name if ob.assigned_officer else "Unassigned"

            items.append(
                ComplianceDeficiencyReportItem(
                    obligation_id=ob.id,
                    obligation_code=ob.obligation_code,
                    title=ob.title,
                    institution_id=ob.institution_id,
                    institution_name=ob.institution.name if ob.institution else "Unknown",
                    category=ob.category,
                    source_reference=ob.source_reference,
                    due_date=due_dt,
                    days_overdue=diff_days,
                    last_review_comments=last_comment,
                    assigned_officer_name=officer_name,
                )
            )

        items.sort(key=lambda x: x.days_overdue, reverse=True)
        return items

    async def export_compliance_csv(
        self,
        current_user: User,
        category: Optional[str] = None,
        status: Optional[str] = None,
        institution_id: Optional[str] = None,
    ) -> str:
        """
        Exports compliance obligations to CSV with complete protection against CSV Formula Injection.
        Prepends a single quote to any cell starting with '=', '+', '-', '@', tab, or newline.
        """
        obs_responses, _ = await self.list_obligations(
            current_user=current_user,
            category=category,
            status=status,
            institution_id=institution_id,
            limit=1000,
            offset=0,
        )

        output = io.StringIO()
        writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL)

        # Header row
        writer.writerow([
            "Obligation Code",
            "Institution Name",
            "Title",
            "Category",
            "Statutory Source",
            "Status",
            "Recurrence",
            "Issue Date (UTC)",
            "Due Date (UTC)",
            "Reviewing Officer",
            "Record Type",
        ])

        for ob in obs_responses:
            record_type = "SYNTHETIC DEMO" if ob.is_synthetic_demonstration else "OFFICIAL STATUTORY"
            writer.writerow([
                sanitize_csv_cell(ob.obligation_code),
                sanitize_csv_cell(ob.institution_name or ""),
                sanitize_csv_cell(ob.title),
                sanitize_csv_cell(ob.category),
                sanitize_csv_cell(ob.source_reference),
                sanitize_csv_cell(ob.status),
                sanitize_csv_cell(ob.recurrence),
                sanitize_csv_cell(ob.issue_date.strftime("%Y-%m-%d %H:%M UTC")),
                sanitize_csv_cell(ob.due_date.strftime("%Y-%m-%d %H:%M UTC")),
                sanitize_csv_cell(ob.assigned_officer_name or "Unassigned"),
                sanitize_csv_cell(record_type),
            ])

        return output.getvalue()
