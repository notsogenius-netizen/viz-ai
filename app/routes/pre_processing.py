import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.schemas import ExternalDBCreateRequest, ExternalDBResponse, CurrentUser, UpdateDBRequest,ExternalDBCreateChatRequest
from app.services.pre_processing import create_or_update_external_db, update_record, post_to_llm, save_query_to_db
from app.services.pre_processing import process_nl_to_sql_query,post_to_nlq_llm,save_nl_sql_query
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


@router.post("/nl-to-sql", status_code=status.HTTP_200_OK)
async def convert_nl_to_sql(data: ExternalDBCreateChatRequest, db: Session = Depends(get_db), current_user: CurrentUser = Depends(get_current_user)):
    url = "http://192.168.1.8:8001/api/nlq/convert_nl_to_sql"
    
    try:
        nlq_data, db_entry_id = await process_nl_to_sql_query(data, db, current_user)
        sql_response = await post_to_nlq_llm(url, nlq_data)
        save_result = await save_nl_sql_query(sql_response, db, db_entry_id)        
        return {
            "status": "success",
            "sql_query": sql_response,
            "save_status": save_result
        }
    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=e.response.status_code,
            detail=f"Error from NL to SQL service: {str(e)}"
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing NL to SQL request: {str(e)}"
        )