from fastapi import Depends, HTTPException, Request, status
from app.utils.jwt import decode_token

def get_current_user(request: Request):
    token = request.cookies.get("access_token")
    print(token)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    payload = decode_token(token)
    if payload is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    
    return {
            "user_id": payload["user_id"],
            "role": payload["role"]
            }