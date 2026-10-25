from typing import List, Optional, Any, Dict
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class OCRExtractedFieldResponse(BaseModel):
    id: str
    ocr_job_id: str
    document_id: str
    application_id: str
    field_name: str
    field_category: str
    raw_value: str
    normalized_value: Optional[str] = None
    confidence: float
    page_number: int
    bounding_box: Optional[Dict[str, Any]] = None
    verification_status: str
    is_automated_advisory: bool
    corrected_value: Optional[str] = None
    review_comments: Optional[str] = None
    reviewed_by_user_id: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class OCRJobResponse(BaseModel):
    id: str
    document_id: str
    application_id: str
    status: str
    engine: str
    page_count: int
    extracted_text_preview: Optional[str] = None
    processing_time_ms: int
    error_message: Optional[str] = None
    fields: List[OCRExtractedFieldResponse] = Field(default_factory=list)
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class OCRFieldVerifyRequest(BaseModel):
    verification_status: str = Field(..., description="VERIFIED, CORRECTED, or REJECTED")
    corrected_value: Optional[str] = Field(None, description="Mandatory when verification_status is CORRECTED")
    review_comments: Optional[str] = Field(None, description="Optional scrutiny officer rationale")
