from app.models.user import UserModel, TenantModel
from fastapi.exceptions import HTTPException
from fastapi import status, Response, Request
from sqlalchemy.exc import IntegrityError
from pydantic import ValidationError
from sqlalchemy.orm import Session
from app.core.settings import settings
from app.utils.crypt import get_password_hash, verify_password
from app.utils.jwt import create_token, decode_token
from app.utils.cookies import set_auth_cookies
from app.utils.auth_dependencies import get_user_role
from app.schemas import LoginUserRequest, CreateUserRequest
from datetime import timedelta
import logging


logger = logging.getLogger("app")

async def create_user(data: CreateUserRequest, response: Response, db: Session):
    logger.info("Attempting to create user with email: %s", data.email)
    try:
        user = db.query(UserModel).filter(UserModel.email == data.email).first()
        if user:
            logger.warning("Email already registered: %s", data.email)
            raise HTTPException(status_code=442, detail="Email is already registered")
        
        new_user = UserModel(
            name=data.name,
            email=data.email,
            password=get_password_hash(data.password),
            tenant_id=data.tenant_id if data.tenant_id else None
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        logger.info("User created successfully: %s", new_user.email)
        
        access_token_data = {"user_id": new_user.id, "role": None}
        access_token = create_token(data=access_token_data, expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))

        refresh_token_data = {"user_id": new_user.id}
        refresh_token = create_token(data=refresh_token_data, expires_delta=timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS))

        new_user.refresh_token = get_password_hash(refresh_token)
        db.commit()
        db.refresh(new_user)
        logger.info("Tokens generated and stored for user: %s", new_user.email)

        return {"access_token": access_token, "refresh_token": refresh_token}
    except HTTPException as http_exc:
        logger.error("HTTPException occurred: %s", http_exc.detail)
        raise http_exc
    except IntegrityError:
        db.rollback()
        logger.error("IntegrityError: User creation failed for email: %s", data.email)
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User already exists or violates constraints")
    except ValidationError as val_err:
        logger.error("ValidationError: %s", str(val_err))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(val_err))
    except Exception as e:
        db.rollback()
        logger.exception("Unexpected error during user creation for email: %s", data.email)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal Server Error")

async def login_user(data: LoginUserRequest, response: Response, db: Session):
    logger.info("Attempting login for email: %s", data.email)
    try:
        user = db.query(UserModel).filter(UserModel.email == data.email).first()
        if not user:
            logger.warning("Login failed: Email not registered: %s", data.email)
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Email not registered. Please signup.")
        
        if not verify_password(data.password, user.password):
            logger.warning("Login failed: Incorrect password for email: %s", data.email)
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Password doesn't match")
        
        access_token_data = {"user_id": str(user.id), "role": None}
        access_token = create_token(data=access_token_data, expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))

        refresh_token_data = {"user_id": str(user.id)}
        refresh_token = create_token(data=refresh_token_data, expires_delta=timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS))

        user.refresh_token = get_password_hash(refresh_token)
        db.commit()
        db.refresh(user)
        logger.info("User logged in successfully: %s", user.email)

        return {"access_token": access_token, "refresh_token": refresh_token}
    except HTTPException as http_exc:
        logger.error("HTTPException during login for email %s: %s", data.email, http_exc.detail)
        raise http_exc
    except ValidationError as val_err:
        logger.error("ValidationError during login for email %s: %s", data.email, str(val_err))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(val_err))
    except IntegrityError:
        db.rollback()
        logger.error("IntegrityError during login for email: %s", data.email)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Database error")
    except Exception:
        db.rollback()
        logger.exception("Unexpected error during login for email: %s", data.email)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal Server Error")

async def logout_user(response: Response, db: Session, user_id: int):
    logger.info("Attempting logout for user_id: %d", user_id)
    try:
        user = db.query(UserModel).filter(UserModel.id == user_id).first()
        if not user:
            logger.warning("Logout failed: User not found with id: %d", user_id)
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        
        user.refresh_token = None
        db.commit()
        db.refresh(user)
        logger.info("User logged out successfully: %d", user_id)

        return {"message": "Logout successful"}
    except HTTPException as http_exc:
        logger.error("HTTPException during logout for user_id %d: %s", user_id, http_exc.detail)
        raise http_exc
    except IntegrityError:
        db.rollback()
        logger.error("IntegrityError during logout for user_id: %d", user_id)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Database error")
    except Exception:
        db.rollback()
        logger.exception("Unexpected error during logout for user_id: %d", user_id)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal Server Error")

async def refresh_user_token(request: Request, response: Response, db: Session):
    try:
         # Get Authorization header
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, 
                detail="Missing or invalid Authorization header"
            )
        refresh_token = auth_header.split(" ")[1]

        if not refresh_token:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing refresh token")

        user = db.query(UserModel).filter(UserModel.refresh_token == refresh_token).first()
        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

        access_token_data= {
            "user_id": str(user.id),
            "role": None
        }

        new_access_token = create_token(data= access_token_data, expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))

        return {"access_message": new_access_token}
    
    except HTTPException as http_exc:
        raise http_exc  # Re-raise known HTTP exceptions

    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Database error")

    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail="An unexpected error occurred"
        )

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