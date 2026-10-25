from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class DocumentVersionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    version_number: int
    storage_key: str
    sha256_hash: str
    file_size: int
    uploaded_by_user_id: str
    scan_status: str
    created_at: datetime


class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    application_id: str
    institution_id: str
    category: str
    original_filename: str
    storage_key: str
    mime_type: str
    file_size: int
    sha256_hash: str
    uploaded_by_user_id: str
    scan_status: str
    scan_result_details: Optional[str] = None
    scan_timestamp: Optional[str] = None
    rejection_reason: Optional[str] = None
    verification_status: str
    current_version: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
    versions: List[DocumentVersionResponse] = []


class ScrutinyFindingCreate(BaseModel):
    category: str
    document_id: Optional[str] = None
    finding_status: str  # ACCEPTED, DEFICIENT, REQUIRES_MANUAL_VERIFICATION
    reason: str
    notes: Optional[str] = None


class ScrutinyFindingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    application_id: str
    document_id: Optional[str] = None
    category: str
    officer_id: str
    finding_status: str
    reason: str
    notes: Optional[str] = None
    is_advisory_ai: bool
    created_at: datetime
    updated_at: datetime
