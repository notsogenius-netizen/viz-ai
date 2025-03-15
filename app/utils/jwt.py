from fastapi import HTTPException, status
from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError
from app.core.settings import settings

def create_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + expires_delta
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode,key= settings.SECRET_KEY, algorithm= settings.ALGORITHM)

def decode_token(token: str):
    try:
        return jwt.decode(token,key= settings.SECRET_KEY, algorithms= settings.ALGORITHM)
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Token has expired"
        )
    
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Invalid token"
        )