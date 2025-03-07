from app.models.user import UserModel
from fastapi.exceptions import HTTPException
from fastapi import status, Response
from sqlalchemy.orm import Session
from app.core.settings import settings
from app.utils.crypt import get_password_hash, verify_password
from app.utils.jwt import create_token, decode_token
from app.utils.cookies import set_auth_cookies
from app.schemas import LoginUserRequest, CreateUserRequest
from datetime import timedelta


async def create_user(data: CreateUserRequest, response: Response, db: Session):
    user = db.query(UserModel).filter(UserModel.email == data.email).first()
    if user:
        raise HTTPException(status_code= 442, detail= "Email is already registered")
    
    new_user = UserModel(
        name = data.name,
        email = data.email,
        password = get_password_hash(data.password),
        tenant_id = data.tenant_id if data.tenant_id else None
    )
    
    access_token_data= {
        "user_id": new_user.id,
        "role": None
    }
    access_token= create_token(data= access_token_data, expires_delta= timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))

    refresh_token_data= {
        "user_id": new_user.id,
    }
    refresh_token= create_token(data= refresh_token_data, expires_delta=timedelta(days= settings.REFRESH_TOKEN_EXPIRE_DAYS))

    new_user.refresh_token = get_password_hash(refresh_token)
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    set_auth_cookies(response, access_token, refresh_token)    
    return new_user

async def login_user(data: LoginUserRequest, response: Response, db: Session):
    user = db.query(UserModel).filter(UserModel.email == data.email).first()
    if not user:
        raise HTTPException(status_code= status.HTTP_404_NOT_FOUND, detail="Email not registered. Please signup.")
    
    if not verify_password(data.password, user.password):
        raise HTTPException(status_code= status.HTTP_401_UNAUTHORIZED, detail="Password doesn't match")
    
    access_token_data= {
        "user_id": user.id,
        "role": None
    }
    access_token= create_token(data= access_token_data, expires_delta= timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))

    refresh_token_data= {
        "user_id": user.id,
    }
    refresh_token= create_token(data= refresh_token_data, expires_delta=timedelta(days= settings.REFRESH_TOKEN_EXPIRE_DAYS))

    user.refresh_token = get_password_hash(refresh_token)
    db.commit()
    db.refresh(user)

    set_auth_cookies(response, access_token, refresh_token)

    return True

async def logout_user(response, db, user_id):
    user = db.query(UserModel).filter(UserModel.id == user_id).first()
    if user:
        user.refresh_token = None
        db.commit()

    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token")