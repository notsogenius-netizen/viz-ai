from app.models.tenant import TenantModel
from fastapi.exceptions import HTTPException

async def create_tenants_service(data, db):
    tenant = db.query(TenantModel).filter(TenantModel.name == data.name).first()

    if tenant:
        raise HTTPException(status_code=442, detail="Tenant already exists")
    
    new_tenant = TenantModel(
        name = data.name,
        super_user_id = None
    )
    db.add(new_tenant)
    db.commit()
    db.refresh(new_tenant)
    return new_tenant