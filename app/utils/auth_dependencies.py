from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from app.models.user import UserProjectRole, RoleModel
from app.schemas import CurrentUser
from app.utils.jwt import decode_token
from uuid import UUID

 
def get_current_user(request: Request):
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header"
        )

    token = auth_header.split("Bearer ")[1]
    
    payload = decode_token(token)
    if payload is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    
    return CurrentUser(user_id= payload["user_id"], role= payload["role"])


def get_user_role(user_id: int, db: Session):
    user_project_roles = db.query(UserProjectRole).filter(UserProjectRole.user_id == user_id).first()
    role = db.query(RoleModel).filter(RoleModel.id == user_project_roles.role_id).first().name
    print(role)
    return role


def get_user_project_role(db: Session, user_id: UUID, role_id: UUID):
    """
    Retrieve the user's project role using user_id and role_id.
    """
    try:
        user_project_role = (
            db.query(UserProjectRole)
            .filter(UserProjectRole.user_id == user_id, UserProjectRole.role_id == role_id)
            .first()
        )

        if not user_project_role:
            raise HTTPException(status_code=404, detail="User project role not found.")

        return user_project_role
    except SQLAlchemyError as e:  # Catch database-related errors
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

    except Exception as e:  # Catch any unexpected errors
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")
