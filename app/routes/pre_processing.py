import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.schemas import ExternalDBCreateRequest, ExternalDBResponse, CurrentUser, UpdateDBRequest
from app.services.pre_processing import create_or_update_external_db, update_record, post_to_llm, save_query_to_db
from app.utils.auth_dependencies import get_current_user
from app.core.db import get_db

router = APIRouter(prefix="/external-db", tags=["External Database"])

@router.post("/", response_model=ExternalDBResponse, status_code=status.HTTP_201_CREATED)
async def create_external_db(data: ExternalDBCreateRequest, db: Session = Depends(get_db), current_user: CurrentUser = Depends(get_current_user)):
    """
    API to connect to an external database, retrieve schema, and store it in the internal database.
    """
    return await create_or_update_external_db(data, db, current_user)


@router.patch("/", status_code=status.HTTP_202_ACCEPTED)
async def update_record_and_call_llm(data: UpdateDBRequest, db: Session = Depends(get_db), current_user: CurrentUser = Depends(get_current_user)):
    """
    API to update external db model and call llm service for processing.
    """
    url = "http://192.168.1.8:8001/queries/"

    data = await update_record(data, db, current_user)
    llm_response = await post_to_llm(url, data)
    response = await save_query_to_db(llm_response, db, db_entry_id= 1)
    return {"status": "success", "queries": llm_response}

# @router.post("/test")
# async def test_route(data: dict):
#     url = "http://192.168.1.9:8001/queries/test"
#     try:
#         llm_response = await post_to_llm(url, data)
#         return {"status": "success", "queries": llm_response}
#     except httpx.HTTPStatusError as e:
#         return {"status": "error", "message": str(e)}