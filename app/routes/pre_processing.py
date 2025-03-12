from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.schemas import ExternalDBCreateRequest, ExternalDBResponse, CurrentUser
from app.services.pre_processing import create_or_update_external_db
from app.utils.auth_dependencies import get_current_user
from app.core.db import get_db

router = APIRouter(prefix="/external-db", tags=["External Database"])

@router.post("/", response_model=ExternalDBResponse, status_code=status.HTTP_201_CREATED)
async def create_external_db(data: ExternalDBCreateRequest, db: Session = Depends(get_db), current_user: CurrentUser = Depends(get_current_user)):
    """
    API to connect to an external database, retrieve schema, and store it in the internal database.
    """
    return await create_or_update_external_db(data, db, current_user)