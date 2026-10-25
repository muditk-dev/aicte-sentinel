from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class DeficiencyItemCreate(BaseModel):
    requirement_title: str
    description: str
    required_corrective_action: str
    document_id: Optional[str] = None


class DeficiencyItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    notice_id: str
    document_id: Optional[str] = None
    requirement_title: str
    description: str
    required_corrective_action: str
    item_status: str
    created_at: datetime


class DeficiencyResponseModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    notice_id: str
    submitted_by_user_id: str
    response_remarks: str
    attachments_json: str
    created_at: datetime


class DeficiencyNoticeCreate(BaseModel):
    officer_remarks: str
    cure_days: Optional[int] = 7  # Configurable statutory cure window
    items: List[DeficiencyItemCreate]


class DeficiencyNoticeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    notice_number: str
    application_id: str
    institution_id: str
    issuing_officer_id: str
    status: str
    due_date: datetime
    officer_remarks: Optional[str] = None
    issued_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    items: List[DeficiencyItemResponse] = []
    responses: List[DeficiencyResponseModel] = []


class DeficiencyResponseSubmit(BaseModel):
    response_remarks: str
    attachment_document_ids: Optional[List[str]] = None


class DeficiencyNoticeReview(BaseModel):
    action: str  # RESOLVE or REOPEN
    officer_remarks: str


class NotificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: Optional[str] = None
    institution_id: Optional[str] = None
    title: str
    message: str
    category: str
    link_url: Optional[str] = None
    is_read: bool
    delivery_status: str
    created_at: datetime
