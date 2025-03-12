from app.models.user import UserModel, TenantModel
from fastapi.exceptions import HTTPException
from fastapi import status, Response, Request
from sqlalchemy.orm import Session
from app.core.settings import settings
from app.utils.crypt import get_password_hash, verify_password
from app.utils.jwt import create_token, decode_token
from app.utils.cookies import set_auth_cookies
from app.utils.auth_dependencies import get_user_role
from app.schemas import LoginUserRequest, CreateUserRequest
from datetime import timedelta


async def create_user(data: CreateUserRequest, response: Response, db: Session):
    try:
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

        return {
            "access_token": access_token,
            "refresh_token": refresh_token
        }
    except Exception as e:
        raise HTTPException(status_code= 500, detail= e)

async def login_user(data: LoginUserRequest, response: Response, db: Session):
    try:
        user = db.query(UserModel).filter(UserModel.email == data.email).first()
        if not user:
            raise HTTPException(status_code= status.HTTP_404_NOT_FOUND, detail="Email not registered. Please signup.")
        
        if not verify_password(data.password, user.password):
            raise HTTPException(status_code= status.HTTP_401_UNAUTHORIZED, detail="Password doesn't match")
        
        role = get_user_role(user_id= user.id, db= db)

        access_token_data= {
            "user_id": user.id,
            "role": role
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

        return {
            "access_token": access_token,
            "refresh_token": refresh_token
        }
    except Exception as e:
        raise HTTPException(status_code= 500, detail= e)

async def logout_user(response, db, user_id):
    try:    
        user = db.query(UserModel).filter(UserModel.id == user_id).first()
        if user:
            user.refresh_token = None
            db.commit()

        response.delete_cookie("access_token")
        response.delete_cookie("refresh_token")
    except Exception as e:
        raise HTTPException(status_code= 500, detail= e)

async def refresh_user_token(request: Request, response: Response, db: Session):
    try:
        refresh_token = request.cookies.get("refresh_token")
        if not refresh_token:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing refresh token")

        user = db.query(UserModel).filter(UserModel.refresh_token == refresh_token).first()
        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

        access_token_data= {
            "user_id": user.id,
            "role": None
        }

        new_access_token = create_token(data= access_token_data, expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))

        response.set_cookie(
            key="access_token",
            value=new_access_token,
            httponly=True,  
            secure=True,    
            samesite="Lax"  
        )

        return {"message": "Access token refreshed"}
    except Exception as e:
        raise HTTPException(status_code= 500, detail= e)

async def create_tenants_service(data, db):
    tenant = db.query(TenantModel).filter(TenantModel.name == data.name).first()

    if tenant:
        raise HTTPException(status_code=442, detail="Tenant already exists")
    
    new_tenant = TenantModel(
        name = data.name,
        super_user_id= data.super_user_id if data.super_user_id else None
    )
    db.add(new_tenant)
    db.commit()
    db.refresh(new_tenant)
    return new_tenant