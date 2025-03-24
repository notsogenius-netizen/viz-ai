from fastapi import APIRouter, status, Depends, Response, Request, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError
from pydantic import ValidationError
from sqlalchemy.orm import Session
from app.core.db import get_db
from app.services.user import create_user, login_user, logout_user, refresh_user_token, create_tenants_service
from app.utils.auth_dependencies import get_current_user
from app.schemas import CreateUserRequest, LoginUserRequest, CreateTenantRequest
import logging


router = APIRouter(
    prefix="/users",
    tags=["User"],
    responses={404: {"description": "Not Found"}}
)

logger = logging.getLogger("app")


@router.post('/signup', status_code= status.HTTP_201_CREATED)
async def signup(data: CreateUserRequest, response: Response, db: Session = Depends(get_db)):
    logger.info("Signup attempt for email: %s", data.email)
    try:
        res = await create_user(data=data, response=response, db=db)
        logger.info("User created successfully: %s", data.email)
        return res
    except HTTPException as http_exc:
        logger.warning("HTTPException during signup for email %s: %s", data.email, http_exc.detail)
        raise
    except ValidationError as val_err:
        logger.error("ValidationError during signup for email %s: %s", data.email, val_err)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(val_err))
    except IntegrityError:
        logger.error("IntegrityError: User already exists with email %s", data.email)
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User already exists or violates constraints")
    except Exception as e:
        logger.exception("Unexpected error during signup for email %s", data.email)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal Server Error")

@router.post('/login', status_code=status.HTTP_200_OK)
async def login(data: LoginUserRequest, response: Response, db: Session = Depends(get_db)):
    logger.info("Login attempt for email: %s", data.email)
    try:
        res = await login_user(data=data, response=response, db=db)
        logger.info("User logged in successfully: %s", data.email)
        return res
    except HTTPException as http_exc:
        logger.warning("HTTPException during login for email %s: %s", data.email, http_exc.detail)
        raise
    except ValidationError as val_err:
        logger.error("ValidationError during login for email %s: %s", data.email, val_err)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(val_err))
    except IntegrityError:
        logger.error("IntegrityError during login for email %s", data.email)
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User already exists or violates constraints")
    except Exception as e:
        logger.exception("Unexpected error during login for email %s", data.email)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal Server Error")

@router.get("/logout")
async def logout(response: Response, db: Session = Depends(get_db), user_id: int = Depends(get_current_user)):
    logger.info("Logout attempt for user_id: %d", user_id)
    try:
        await logout_user(response, db, user_id)
        logger.info("User logged out successfully: %d", user_id)
        return {"message": "Logged out successfully"}
    except HTTPException as http_exc:
        logger.warning("HTTPException during logout for user_id %d: %s", user_id, http_exc.detail)
        raise
    except IntegrityError:
        db.rollback()
        logger.error("IntegrityError during logout for user_id %d", user_id)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Database error")
    except Exception:
        db.rollback()
        logger.exception("Unexpected error during logout for user_id %d", user_id)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal Server Error")

@router.get('/get-user')
async def get_user(data=Depends(get_current_user)):
    logger.info("Fetching user data")
    try:
        if not data:
            logger.warning("Unauthorized access attempt")
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")
        logger.info("User data retrieved successfully")
        return data
    except HTTPException as http_exc:
        logger.warning("HTTPException during get-user: %s", http_exc.detail)
        raise
    except Exception:
        logger.exception("Unexpected error during get-user")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected error occurred")

@router.get('/refresh-token')
async def refresh_token(request: Request, response: Response, db: Session = Depends(get_db)):
    logger.info("Token refresh attempt")
    try:
        res = await refresh_user_token(request, response, db)
        logger.info("Token refreshed successfully")
        return res
    except HTTPException as http_exc:
        logger.warning("HTTPException during token refresh: %s", http_exc.detail)
        raise
    except Exception:
        logger.exception("Unexpected error during token refresh")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected error occurred")