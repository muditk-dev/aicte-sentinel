from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class AuditEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    sequence_number: int
    actor_id: str
    action: str
    resource_type: str
    resource_id: str
    ip_address: Optional[str]
    previous_entry_hash: str
    payload_hash: str
    entry_hash: str
    details_json: Optional[str]
    created_at: datetime


class AuditVerificationResponse(BaseModel):
    is_valid: bool
    total_events_checked: int
    last_verified_sequence: int
    broken_sequence_id: Optional[str] = None
    chain_head_hash: Optional[str] = None
    verification_message: str
