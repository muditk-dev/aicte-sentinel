from typing import List, Optional, Any, Dict
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class WorkflowVersionBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    version_number: int
    aph_edition: str
    is_published: bool
    created_at: datetime


class WorkflowTemplateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    code: str
    name: str
    description: Optional[str] = None
    category: str
    is_active: bool
    versions: List[WorkflowVersionBrief] = []


class WorkflowVersionDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    template_id: str
    version_number: int
    aph_edition: str
    state_machine_json: str
    checklist_rules_json: str
    is_published: bool
    proposed_by_user_id: Optional[str]
    approved_by_user_id: Optional[str]
    approval_timestamp: Optional[str]
    created_at: datetime
