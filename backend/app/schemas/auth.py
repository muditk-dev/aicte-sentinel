from typing import List, Optional
from pydantic import BaseModel, EmailStr, ConfigDict


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RoleBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    code: str
    name: str


class UserProfile(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: str
    full_name: str
    designation: Optional[str] = None
    institution_id: Optional[str] = None
    institution_name: Optional[str] = None
    assigned_region: Optional[str] = None
    roles: List[RoleBrief]


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "Bearer"
    expires_in_minutes: int
    user: UserProfile


class BootstrapStatusResponse(BaseModel):
    bootstrap_available: bool
    total_users: int
    message: str


class BootstrapRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    designation: Optional[str] = "Member Secretary / Central Council"
    assigned_region: Optional[str] = None


class ProvisionUserRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    role_code: str
    designation: Optional[str] = None
    institution_id: Optional[str] = None
    assigned_region: Optional[str] = None

