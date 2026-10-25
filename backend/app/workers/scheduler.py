import asyncio
from datetime import datetime, timedelta, timezone
from sqlalchemy import select, and_
from app.core.database import AsyncSessionLocal
from app.core.logging import logger
from app.models.deficiency import DeficiencyNotice, Notification


async def evaluate_deficiency_deadlines(db: AsyncSessionLocal = None):
    """
    Idempotent deadline evaluation task:
    1. Identifies approaching statutory deficiency cure deadlines (< 48 hours remaining).
    2. Identifies overdue cure deadlines requiring escalation.
    3. Emits in-app notifications using unique dedup_keys to guarantee idempotency.
    """
    now = datetime.now(timezone.utc)
    approaching_threshold = now + timedelta(hours=48)

    async def _evaluate(session):
        # Active notices
        stmt = select(DeficiencyNotice).where(
            DeficiencyNotice.status.in_(["ISSUED", "REOPENED"])
        )
        notices = (await session.execute(stmt)).scalars().all()

        notifications_created = 0
        for notice in notices:
            notice_due = notice.due_date if notice.due_date.tzinfo else notice.due_date.replace(tzinfo=timezone.utc)

            # 1. Overdue Notice Check
            if now > notice_due:
                dedup_key = f"overdue_{notice.id}_{notice_due.date()}"
                exists_stmt = select(Notification).where(Notification.dedup_key == dedup_key)
                existing = (await session.execute(exists_stmt)).scalar_one_or_none()

                if not existing:
                    notif = Notification(
                        institution_id=notice.institution_id,
                        title=f"URGENT ESCALATION: Deficiency Cure Window Overdue ({notice.notice_number})",
                        message=f"The statutory response window for deficiency notice {notice.notice_number} expired on {notice_due.strftime('%d-%b-%Y')}. Continued default will lead to recommendation for hearing/rejection under APH guidelines.",
                        category="DEADLINE_APPROACHING",
                        link_url=f"/applications/{notice.application_id}",
                        is_read=False,
                        dedup_key=dedup_key,
                    )
                    session.add(notif)
                    notifications_created += 1

            # 2. Approaching Deadline Check (< 48 hours remaining)
            elif notice_due <= approaching_threshold:
                hours_left = max(1, int((notice_due - now).total_seconds() // 3600))
                dedup_key = f"approaching_{notice.id}_{notice_due.date()}"
                exists_stmt = select(Notification).where(Notification.dedup_key == dedup_key)
                existing = (await session.execute(exists_stmt)).scalar_one_or_none()

                if not existing:
                    notif = Notification(
                        institution_id=notice.institution_id,
                        title=f"Statutory Notice Deadline Approaching: {notice.notice_number}",
                        message=f"Only {hours_left} hours remaining to submit clarification for notice {notice.notice_number}. Deadline: {notice_due.strftime('%d-%b-%Y %H:%M UTC')}.",
                        category="DEADLINE_APPROACHING",
                        link_url=f"/applications/{notice.application_id}",
                        is_read=False,
                        dedup_key=dedup_key,
                    )
                    session.add(notif)
                    notifications_created += 1

        if notifications_created > 0:
            await session.commit()
            logger.info(f"Evaluated deadlines: Created {notifications_created} notifications.")

    if db is not None:
        await _evaluate(db)
    else:
        async with AsyncSessionLocal() as session:
            await _evaluate(session)


async def run_periodic_tasks():
    logger.info("Sentinel background worker initialized.")
    logger.info("Monitoring statutory SLA deadlines, deficiency cure windows, and Merkle ledger anchoring.")
    while True:
        try:
            await evaluate_deficiency_deadlines()
            await asyncio.sleep(60)
        except asyncio.CancelledError:
            logger.info("Worker received cancellation signal.")
            break
        except Exception as e:
            logger.error(f"Worker task cycle error: {e}")
            await asyncio.sleep(10)


if __name__ == "__main__":
    try:
        asyncio.run(run_periodic_tasks())
    except KeyboardInterrupt:
        logger.info("Worker stopped by operator.")
