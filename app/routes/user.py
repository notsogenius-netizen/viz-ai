from fastapi import APIRouter, status, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from app.core.db import get_db
from app.services.user import create_user_account, login_user
from app.schemas import CreateUserRequest, LoginUserRequest

router = APIRouter(
    prefix="/users",
    tags=["User"],
    responses={404: {"description": "Not Found"}}
)

@router.post('/signup', status_code= status.HTTP_201_CREATED)
async def signup(data: CreateUserRequest, db: Session = Depends(get_db)):
    await create_user_account(data= data, db= db)
    return JSONResponse(content= {"message": "User account has been created."})

@router.post('/login', status_code= status.HTTP_200_OK)
async def login(data: LoginUserRequest, db: Session = Depends(get_db)):
    user = await login_user(data= data, db= db)
    return JSONResponse(content={"message": "User is logged in"})