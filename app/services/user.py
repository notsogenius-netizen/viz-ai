from app.models.user import UserModel
from fastapi.exceptions import HTTPException
from fastapi import status
from sqlalchemy.orm import Session
from app.utils.crypt import get_password_hash, verify_password
from app.schemas import LoginUserRequest, CreateUserRequest

async def create_user_account(data: CreateUserRequest, db: Session):
    user = db.query(UserModel).filter(UserModel.email == data.email).first()
    if user:
        raise HTTPException(status_code= 442, detail= "Email is already registered")
    
    new_user = UserModel(
        name = data.name,
        email = data.email,
        password = get_password_hash(data.password),
        tenant_id = data.tenant_id if data.tenant_id else None
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

async def login_user(data: LoginUserRequest, db: Session):
    user = db.query(UserModel).filter(UserModel.email == data.email).first()
    if not user:
        raise HTTPException(status_code= status.HTTP_404_NOT_FOUND, detail="Email not registered. Please signup.")
    
    if not verify_password(data.password, user.password):
        raise HTTPException(status_code= status.HTTP_401_UNAUTHORIZED, detail="Password doesn't match")
    
    return True