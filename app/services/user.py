from app.models.user import UserModel
from fastapi.exceptions import HTTPException

async def create_user_account(data, db):
    user = db.query(UserModel).filter(UserModel.email == data.email).first()
    if user:
        raise HTTPException(status_code= 442, detail= "Email is already registered")
    
    new_user = UserModel(
        name = data.name,
        email = data.email,
        password = data.password,
        tenant_id = data.tenant_id
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user