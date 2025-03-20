from pydantic import BaseModel, EmailStr
from typing import Optional, Any, List
from uuid import UUID

class CreateUserRequest(BaseModel):
    name: str
    email: EmailStr
    password: str
    tenant_id: Optional[UUID] = None

class CreateTenantRequest(BaseModel):
    name: str
    super_user_id: Optional[UUID] = None

class LoginUserRequest(BaseModel):
    email: str
    password: str

class ExternalDBCreate(BaseModel):
    user_project_role_id: UUID
    connection_string: str
    domain: str


class ExternalDBCreateRequest(BaseModel):
    project_id: str
    role: str
    connection_string: str
    domain: Optional[str] = None
    db_type: str
    api_key: Optional[str] = None

class ExternalDBResponse(BaseModel):
    db_entry_id: UUID

class UpdateDBRequest(BaseModel):
    project_id: str
    db_entry_id: str
    domain: str
    api_key: Optional[str] =None

class CurrentUser(BaseModel):
    user_id: UUID
    role: Optional[str] = None
    
class NLQResponse(BaseModel):
    api_key:Optional[str]=None
    nl_query: str
    db_schema: str
    db_type: str
    
class ExternalDBCreateChatRequest(BaseModel):
    nl_query:str
    
class ExecuteQueryRequest(BaseModel):
    external_db_id: UUID
    query_id: UUID


class CreateDefaultDashboardRequest(BaseModel):
    name: Optional[str] = None
    external_db_id: UUID
    query_ids: List[UUID]