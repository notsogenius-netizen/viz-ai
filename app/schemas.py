from pydantic import BaseModel, EmailStr, UUID4

class CreateUserRequest(BaseModel):
    name: str
    email: EmailStr
    password: str
    tenant_id: UUID4

class CreateTenantRequest(BaseModel):
    name: str