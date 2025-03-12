from pydantic import BaseModel, EmailStr
from typing import Optional, Dict, Any

class CreateUserRequest(BaseModel):
    name: str
    email: EmailStr
    password: str
    tenant_id: Optional[int] = None

class CreateTenantRequest(BaseModel):
    name: str
    super_user_id: Optional[int] = None

class LoginUserRequest(BaseModel):
    email: str
    password: str

class ExternalDBCreate(BaseModel):
    user_project_role_id: int
    connection_string: str
    domain: str


class ExternalDBCreateRequest(BaseModel):
    project_id: int
    connection_string: str
    domain: str

class ExternalDBResponse(BaseModel):
    user_role: str
    connection_string: str
    domain: str
    db_metadata: Optional[str] = None
    schema_structure_string: str

class UpdateDBRequest(BaseModel):
    db_entry_id: int
    domain: str

class CurrentUser(BaseModel):
    user_id: int
    role: str