from fastapi import APIRouter, status, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from app.core.db import get_db
from app.services.tenants import create_tenants_service
from app.schemas import CreateTenantRequest

router = APIRouter(
    prefix="/tenants",
    tags=["Tenant"],
    responses={404: {"description": "Not Found"}}
)

@router.post('/create-tenant', status_code= status.HTTP_201_CREATED)
async def create_tenant(data: CreateTenantRequest, db: Session = Depends(get_db)):
    await create_tenants_service(data= data, db= db)
    return JSONResponse(content= {"message": "Tenant has been registered"})