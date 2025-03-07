from fastapi import APIRouter, status, Depends, Response, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from app.core.db import get_db
from app.services.user import create_user, login_user, logout_user
from app.utils.auth_dependencies import get_current_user
from app.schemas import CreateUserRequest, LoginUserRequest

router = APIRouter(
    prefix="/users",
    tags=["User"],
    responses={404: {"description": "Not Found"}}
)

@router.post('/signup', status_code= status.HTTP_201_CREATED)
async def signup(data: CreateUserRequest,response: Response, db: Session = Depends(get_db)):
    await create_user(data= data, response= response, db= db)
    return {"message": "User signed up"}

@router.post('/login', status_code= status.HTTP_200_OK)
async def login(data: LoginUserRequest, response: Response, db: Session = Depends(get_db)):
    user = await login_user(data= data, response= response, db= db)
    return {"message": "User logged in"}
        

@router.get("/logout")
async def logout(response: Response, db: Session = Depends(get_db), user_id: int = Depends(get_current_user)):
    await logout_user(response, db, user_id)
    return {"message": "Logged out successfully"}

@router.get('/get-user')
async def get_user(data = Depends(get_current_user)):
    return data