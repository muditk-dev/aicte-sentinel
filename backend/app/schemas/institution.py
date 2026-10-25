from typing import Optional
from datetime import datetime
from pydantic import BaseModel, EmailStr, ConfigDict


class InstitutionCreate(BaseModel):
    name: str
    code: str
    region: str
    state: str
    district: str
    institution_type: str
    established_year: Optional[int] = None
    contact_email: EmailStr
    contact_phone: str
    address: Optional[str] = None


class InstitutionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    code: str
    region: str
    state: str
    district: str
    institution_type: str
    established_year: Optional[int]
    status: str
    contact_email: str
    contact_phone: str
    address: Optional[str]
    created_at: datetime
    updated_at: datetime
