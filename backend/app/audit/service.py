import hashlib
import json
from typing import Any, Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from app.models.audit import AuditEvent
from app.schemas.audit import AuditVerificationResponse

GENESIS_HASH = "0000000000000000000000000000000000000000000000000000000000000000"


def calculate_hash(data: str) -> str:
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


async def record_audit_event(
    db: AsyncSession,
    actor_id: str,
    action: str,
    resource_type: str,
    resource_id: str,
    details: Optional[Dict[str, Any]] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> AuditEvent:
    """
    Appends an immutable, cryptographically chained audit record.
    """
    details_str = json.dumps(details or {}, sort_keys=True)
    payload_hash = calculate_hash(details_str)

    # Fetch last audit event for chain continuity
    stmt = select(AuditEvent).order_by(desc(AuditEvent.sequence_number)).limit(1)
    result = await db.execute(stmt)
    last_event = result.scalar_one_or_none()

    if last_event:
        prev_hash = last_event.entry_hash
        new_seq = last_event.sequence_number + 1
    else:
        prev_hash = GENESIS_HASH
        new_seq = 1

    # Chained hash formula
    entry_payload = f"{prev_hash}|{new_seq}|{actor_id}|{action}|{resource_type}|{resource_id}|{payload_hash}"
    entry_hash = calculate_hash(entry_payload)

    audit_entry = AuditEvent(
        sequence_number=new_seq,
        actor_id=actor_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        ip_address=ip_address,
        user_agent=user_agent,
        previous_entry_hash=prev_hash,
        payload_hash=payload_hash,
        entry_hash=entry_hash,
        details_json=details_str,
    )

    db.add(audit_entry)
    await db.flush()
    return audit_entry


async def verify_audit_chain(db: AsyncSession) -> AuditVerificationResponse:
    """
    Validates cryptographic integrity of the entire audit chain.
    Detects any tampering, alteration, or out-of-order sequence insertion.
    """
    stmt = select(AuditEvent).order_by(AuditEvent.sequence_number.asc())
    result = await db.execute(stmt)
    events = result.scalars().all()

    if not events:
        return AuditVerificationResponse(
            is_valid=True,
            total_events_checked=0,
            last_verified_sequence=0,
            verification_message="Audit log is currently empty (Genesis state)."
        )

    expected_prev = GENESIS_HASH
    for event in events:
        # 1. Verify previous hash linkage
        if event.previous_entry_hash != expected_prev:
            return AuditVerificationResponse(
                is_valid=False,
                total_events_checked=len(events),
                last_verified_sequence=event.sequence_number - 1,
                broken_sequence_id=event.id,
                verification_message=f"Hash chain broken at sequence {event.sequence_number}: previous_entry_hash mismatch."
            )

        # 2. Verify payload hash
        recalc_payload_hash = calculate_hash(event.details_json or "{}")
        if recalc_payload_hash != event.payload_hash:
            return AuditVerificationResponse(
                is_valid=False,
                total_events_checked=len(events),
                last_verified_sequence=event.sequence_number - 1,
                broken_sequence_id=event.id,
                verification_message=f"Payload tamper detected at sequence {event.sequence_number}: payload_hash mismatch."
            )

        # 3. Recalculate entry hash
        recalc_entry_payload = f"{event.previous_entry_hash}|{event.sequence_number}|{event.actor_id}|{event.action}|{event.resource_type}|{event.resource_id}|{event.payload_hash}"
        recalc_entry_hash = calculate_hash(recalc_entry_payload)
        if recalc_entry_hash != event.entry_hash:
            return AuditVerificationResponse(
                is_valid=False,
                total_events_checked=len(events),
                last_verified_sequence=event.sequence_number - 1,
                broken_sequence_id=event.id,
                verification_message=f"Entry signature invalid at sequence {event.sequence_number}."
            )

        expected_prev = event.entry_hash

    return AuditVerificationResponse(
        is_valid=True,
        total_events_checked=len(events),
        last_verified_sequence=events[-1].sequence_number,
        chain_head_hash=events[-1].entry_hash,
        verification_message=f"Cryptographic chain verified. All {len(events)} events are intact and untampered."
    )
