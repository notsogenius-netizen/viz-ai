from pydantic import BaseModel, EmailStr, UUID4
from typing import Optional

class CreateUserRequest(BaseModel):
    name: str
    email: EmailStr
    password: str
    tenant_id: Optional[UUID4] = None

class CreateTenantRequest(BaseModel):
    name: str
    super_user_id: Optional[UUID4] = None

class LoginUserRequest(BaseModel):
    email: str
    password: str