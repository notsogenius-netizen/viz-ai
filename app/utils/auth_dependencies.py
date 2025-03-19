from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.models.user import UserProjectRole, RoleModel
from app.schemas import CurrentUser
from app.utils.jwt import decode_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/users/login")  
def get_current_user(token: str = Depends(oauth2_scheme)):
    if token is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token missing")
    print(token)
    payload = decode_token(token)
    if payload is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    
    return CurrentUser(user_id= payload["user_id"], role= payload["role"])

def get_user_role(user_id: int, db: Session):
    user_project_roles = db.query(UserProjectRole).filter(UserProjectRole.user_id == user_id).first()
    role = db.query(RoleModel).filter(RoleModel.id == user_project_roles.role_id).first().name
    print(role)
    return role