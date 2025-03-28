from pydantic import BaseModel, EmailStr
from typing import Optional, Any, List
from uuid import UUID
from datetime import datetime
from dataclasses import dataclass, asdict

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
    connection_string: Optional[str] = None
    domain: Optional[str] = None
    db_type: Optional[str] = None
    api_key: Optional[str] = None
    password:Optional[str] = None
    host:Optional[str] = None
    db_name:Optional[str] = None
    name:Optional[str] = None
    
    

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
    
@dataclass
class QueryWithId(BaseModel):
    query_id: str
    query: str
    explanation:str
    

class TimeBasedQueriesUpdateRequest(BaseModel):
    queries: List[QueryWithId]
    min_date: str
    max_date: str
    db_type: str     
class QueryDateUpdateResponse(BaseModel):
    query_id: UUID 
    original_query: str 
    updated_query: str 
    original_explanation:str
    updated_explanation:str
    success: bool 
    error: Optional[str] = None

class TimeBasedQueriesUpdateResponse(BaseModel):
    updated_queries: List[QueryDateUpdateResponse]
    
class TimeBasedUpdateRequest(BaseModel):
    dashboard_id: UUID
    min_date: str
    max_date: str
    
class DashboardSchema(BaseModel):
    dashboard_id: UUID
    dashboard_name: str

    class Config:
        orm_mode = True

class CreateDefaultDashboardRequest(BaseModel):
    name: Optional[str] = None
    db_entry_id: UUID
    role_id: UUID

class AddQueriesToDashboardRequest(BaseModel):
    name: Optional[str] = None
    dashboard_id: UUID
    query_ids: List[UUID]

class DashboardResponse(BaseModel):
    id: UUID
    name: str
    created_at: datetime
    external_db_id: UUID

    class Config:
        orm_mode = True

class DashboardQueryDeleteRequest(BaseModel):
    dashboard_id: UUID
    query_ids: list[UUID]