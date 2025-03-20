from fastapi import APIRouter, status, Depends, Response, Request, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError
from pydantic import ValidationError
from sqlalchemy.orm import Session
from app.core.db import get_db
from app.services.user import create_user, login_user, logout_user, refresh_user_token, create_tenants_service
from app.utils.auth_dependencies import get_current_user
from app.schemas import CreateUserRequest, LoginUserRequest, CreateTenantRequest

router = APIRouter(
    prefix="/users",
    tags=["User"],
    responses={404: {"description": "Not Found"}}
)

@router.post('/signup', status_code= status.HTTP_201_CREATED)
async def signup(data: CreateUserRequest,response: Response, db: Session = Depends(get_db)):
    try:
        res = await create_user(data= data, response= response, db= db)
        return res
    except HTTPException as http_exc:
        raise http_exc  # Re-raise known HTTP exceptions
    except ValidationError as val_err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(val_err))
    except IntegrityError as int_err:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User already exists or violates constraints")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal Server Error")

@router.post('/login', status_code= status.HTTP_200_OK)
async def login(data: LoginUserRequest, response: Response, db: Session = Depends(get_db)):
    res = await login_user(data= data, response= response, db= db)
    return res
        

@router.get("/logout")
async def logout(response: Response, db: Session = Depends(get_db), user_id: int = Depends(get_current_user)):
    await logout_user(response, db, user_id)
    return {"message": "Logged out successfully"}

@router.get('/get-user')
async def get_user(data = Depends(get_current_user)):
    return data

@router.get('/refresh-token')
async def refresh_token(request: Request, response: Response, db: Session = Depends(get_db)):
    res = await refresh_user_token(request, response, db)
    return res

@router.post('/create-tenant', status_code= status.HTTP_201_CREATED)
async def create_tenant(data: CreateTenantRequest, db: Session = Depends(get_db)):
    await create_tenants_service(data= data, db= db)
    return JSONResponse(content= {"message": "Tenant has been registered"})