from fastapi import HTTPException, status
from datetime import datetime, timedelta, timezone
from jwt.exceptions import ExpiredSignatureError, InvalidTokenError
from app.core.settings import settings
import jwt

def create_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=120))
    
    to_encode.update({"exp": expire})
    
    return jwt.encode(to_encode, key=settings.SECRET_KEY, algorithm=settings.ALGORITHM)

def decode_token(token: str):
    try:
        return jwt.decode(token, key=settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Token has expired"
        )
    except InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Invalid token"
        )