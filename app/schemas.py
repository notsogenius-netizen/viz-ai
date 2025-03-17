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
    domain: Optional[str] = None
    db_type: str
    api_key: str

class ExternalDBResponse(BaseModel):
    role: str
    db_schema: str
    db_type: str
    domain: str
    min_date: Optional[str] = None
    max_date: Optional[str] = None
    api_key:Optional[str] = None
    db_metadata: Optional[str] = None

class   UpdateDBRequest(BaseModel):
    db_entry_id: int
    domain: str

class CurrentUser(BaseModel):
    user_id: int
    role: str
    
class NLQResponse(BaseModel):
    api_key:Optional[str]=None
    nl_query: str
    db_schema: str
    db_type: str
    
class ExternalDBCreateChatRequest(BaseModel):
    nl_query:str
    