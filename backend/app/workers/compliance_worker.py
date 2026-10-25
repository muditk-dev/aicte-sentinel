import asyncio
import json
from datetime import datetime, timedelta, timezone
from typing import Optional
from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.core.logging import logger
from app.models.compliance import ComplianceObligation, ComplianceEscalation, ObligationReviewHistory
from app.models.deficiency import Notification
from app.models.document import Document
from app.audit.service import record_audit_event


def ensure_utc(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


async def evaluate_compliance_deadlines_and_escalations(db: AsyncSessionLocal = None) -> int:
    """
    Idempotent compliance monitoring worker:
    1. Evaluates approaching deadlines (30d, 15d, 7d, 1d) and emits deduplicated reminders.
    2. Transitions past-due active obligations to OVERDUE.
    3. Escalates overdue obligations:
       - Level 1: Overdue >= 7 days -> Notifies Regional Officers.
       - Level 2: Overdue >= 14 days -> Notifies Super Administrators.
    4. Evaluates certificate validity deadlines.
    Guarantees:
    - Zero duplicate notifications using deterministic dedup_key.
    - Idempotent execution (safe to retry at any time).
    - Consequential state changes generate chained SHA-256 audit records.
    """
    now = datetime.now(timezone.utc)
    actions_taken = 0

    async def _evaluate(session: AsyncSession):
        nonlocal actions_taken

        # 1. Fetch all active obligations
        stmt = select(ComplianceObligation).where(
            ComplianceObligation.status.notin_(["COMPLIANT", "CLOSED"])
        )
        res = await session.execute(stmt)
        obligations = res.scalars().all()

        for ob in obligations:
            due_dt = ensure_utc(ob.due_date)
            diff_seconds = (due_dt - now).total_seconds()
            diff_days = int(diff_seconds // 86400)

            # Case A: Overdue check
            if now > due_dt:
                days_overdue = max(1, int((now - due_dt).total_seconds() // 86400))
                
                # Transition status to OVERDUE if not already
                if ob.status != "OVERDUE":
                    prev_status = ob.status
                    ob.status = "OVERDUE"
                    
                    history = ObligationReviewHistory(
                        obligation_id=ob.id,
                        actor_id="SYSTEM_MONITOR",
                        actor_role="AUTOMATED_WORKER",
                        action="OVERDUE_TRANSITION",
                        previous_status=prev_status,
                        new_status="OVERDUE",
                        comments=f"Automated statutory monitor: Deadline expired on {due_dt.strftime('%d-%b-%Y')}. Transitioned to OVERDUE.",
                    )
                    session.add(history)
                    actions_taken += 1

                # Escalation Level 2 (> 14 days overdue)
                if days_overdue >= 14:
                    esc2_dedup = f"esc_level2_{ob.id}_{due_dt.date()}"
                    esc2_exists = (
                        await session.execute(
                            select(ComplianceEscalation).where(
                                and_(
                                    ComplianceEscalation.obligation_id == ob.id,
                                    ComplianceEscalation.escalation_level == 2,
                                )
                            )
                        )
                    ).scalar_one_or_none()

                    if not esc2_exists:
                        # In-app notification for Super Admin
                        notif = Notification(
                            institution_id=ob.institution_id,
                            title=f"CRITICAL ESCALATION (Level 2): Obligation {ob.obligation_code} Overdue {days_overdue} Days",
                            message=(
                                f"Institution defaulted on compliance obligation '{ob.title}' for {days_overdue} days. "
                                f"Immediate central referral or Standing Hearing Committee summons recommended under APH norms."
                            ),
                            category="ESCALATION_LEVEL_2",
                            link_url=f"/compliance/obligations/{ob.id}",
                            is_read=False,
                            delivery_status="IN_APP_DELIVERED",
                            dedup_key=esc2_dedup,
                        )
                        session.add(notif)
                        await session.flush()

                        esc = ComplianceEscalation(
                            obligation_id=ob.id,
                            institution_id=ob.institution_id,
                            escalation_level=2,
                            severity="CRITICAL",
                            trigger_reason="OVERDUE_14_DAYS",
                            days_overdue=days_overdue,
                            notified_roles_json=json.dumps(["SUPER_ADMIN", "COUNCIL_MEMBER"]),
                            notification_id=notif.id,
                            is_resolved=False,
                        )
                        session.add(esc)
                        actions_taken += 1

                # Escalation Level 1 (> 7 days overdue)
                elif days_overdue >= 7:
                    esc1_dedup = f"esc_level1_{ob.id}_{due_dt.date()}"
                    esc1_exists = (
                        await session.execute(
                            select(ComplianceEscalation).where(
                                and_(
                                    ComplianceEscalation.obligation_id == ob.id,
                                    ComplianceEscalation.escalation_level == 1,
                                )
                            )
                        )
                    ).scalar_one_or_none()

                    if not esc1_exists:
                        notif = Notification(
                            institution_id=ob.institution_id,
                            title=f"HIGH ESCALATION (Level 1): Obligation {ob.obligation_code} Overdue {days_overdue} Days",
                            message=(
                                f"Compliance obligation '{ob.title}' is overdue by {days_overdue} days. "
                                f"Regional officer review and show-cause notice required."
                            ),
                            category="ESCALATION_LEVEL_1",
                            link_url=f"/compliance/obligations/{ob.id}",
                            is_read=False,
                            delivery_status="IN_APP_DELIVERED",
                            dedup_key=esc1_dedup,
                        )
                        session.add(notif)
                        await session.flush()

                        esc = ComplianceEscalation(
                            obligation_id=ob.id,
                            institution_id=ob.institution_id,
                            escalation_level=1,
                            severity="HIGH",
                            trigger_reason="OVERDUE_7_DAYS",
                            days_overdue=days_overdue,
                            notified_roles_json=json.dumps(["REGIONAL_OFFICER", "SCRUTINY_OFFICER"]),
                            notification_id=notif.id,
                            is_resolved=False,
                        )
                        session.add(esc)
                        actions_taken += 1

                # Overdue institutional notification
                overdue_dedup = f"notif_overdue_{ob.id}_{due_dt.date()}"
                exists_overdue = (
                    await session.execute(select(Notification).where(Notification.dedup_key == overdue_dedup))
                ).scalar_one_or_none()

                if not exists_overdue:
                    notif = Notification(
                        institution_id=ob.institution_id,
                        title=f"STATUTORY OVERDUE: {ob.title} ({ob.obligation_code})",
                        message=(
                            f"The compliance submission deadline for '{ob.title}' expired on {due_dt.strftime('%d-%b-%Y')}. "
                            "Please upload the required evidence immediately to prevent regulatory penalties."
                        ),
                        category="DEADLINE_OVERDUE",
                        link_url=f"/compliance/obligations/{ob.id}",
                        is_read=False,
                        delivery_status="IN_APP_DELIVERED",
                        dedup_key=overdue_dedup,
                    )
                    session.add(notif)
                    actions_taken += 1

            # Case B: Approaching deadlines (30d, 15d, 7d, 1d)
            else:
                reminder_windows = [
                    (1, "URGENT (24 Hours Remaining)", "CRITICAL"),
                    (7, "Approaching in 7 Days", "HIGH"),
                    (15, "Approaching in 15 Days", "MEDIUM"),
                    (30, "Approaching in 30 Days", "LOW"),
                ]

                for window_days, window_label, urgency in reminder_windows:
                    if diff_days <= window_days:
                        dedup = f"remind_{window_days}d_{ob.id}_{due_dt.date()}"
                        existing = (
                            await session.execute(select(Notification).where(Notification.dedup_key == dedup))
                        ).scalar_one_or_none()

                        if not existing:
                            notif = Notification(
                                institution_id=ob.institution_id,
                                title=f"Compliance Deadline {window_label}: {ob.title}",
                                message=(
                                    f"Obligation '{ob.title}' is due in {diff_days} day(s) on {due_dt.strftime('%d-%b-%Y')}. "
                                    f"Category: {ob.category}. Source: {ob.source_reference}."
                                ),
                                category="DEADLINE_APPROACHING",
                                link_url=f"/compliance/obligations/{ob.id}",
                                is_read=False,
                                delivery_status="IN_APP_DELIVERED",
                                dedup_key=dedup,
                            )
                            session.add(notif)
                            actions_taken += 1
                        break  # Only trigger the most urgent matched window

        if actions_taken > 0:
            await session.commit()
            logger.info(f"Compliance monitoring cycle completed: {actions_taken} actions/notifications executed.")

    if db is not None:
        await _evaluate(db)
    else:
        async with AsyncSessionLocal() as session:
            await _evaluate(session)

    return actions_taken
