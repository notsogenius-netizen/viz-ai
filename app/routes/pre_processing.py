import httpx
import logging
from fastapi import APIRouter, Depends, HTTPException, status,Body
from sqlalchemy.orm import Session
from app.schemas import ExternalDBCreateRequest, ExternalDBResponse, CurrentUser, UpdateDBRequest,ExternalDBCreateChatRequest
from app.services.pre_processing import create_or_update_external_db, update_record, post_to_llm, save_query_to_db
from app.services.pre_processing import process_nl_to_sql_query,post_to_nlq_llm,save_nl_sql_query
from app.utils.auth_dependencies import get_current_user
from app.core.db import get_db
from app.core.settings import settings

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
    base_uri = settings.LLM_URI
    url = f"{base_uri}/queries/"

    saved_data = await update_record(data, db, current_user)
    llm_response = await post_to_llm(url, saved_data)
    response = await save_query_to_db(queries=llm_response, db= db, db_entry_id= data.db_entry_id)
    return response

logger = logging.getLogger(__name__)
@router.post("/nl-to-sql", status_code=status.HTTP_200_OK)
async def convert_nl_to_sql(data: ExternalDBCreateChatRequest = Body(...), db: Session = Depends(get_db), current_user: CurrentUser = Depends(get_current_user)):
        base_uri = settings.LLM_URI
        url = f"{base_uri}/api/nlq/convert_nl_to_sql"
        print("Recivied data",data)
        try:              
            logger.info("Received NL query: %s", data.nl_query)
            nlq_data, db_entry_id = await process_nl_to_sql_query(data, db, current_user)
            logger.info("Processed NL to SQL Query, Data: %s, DB Entry ID: %s", nlq_data, db_entry_id)
            sql_response = await post_to_nlq_llm(url, nlq_data)
            # logger.info("Received SQL response: %s", sql_response)

            save_result = await save_nl_sql_query(sql_response, db, db_entry_id)        
            logger.info("Save result: %s", save_result)

            return {
                "status": "success",
                "sql_query": sql_response,
                "save_status": save_result
            }

        except httpx.HTTPStatusError as e:
            logger.error("Error from NL to SQL service: %s", str(e))
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"Error from NL to SQL service: {str(e)}"
            )
    
        except HTTPException as e:
            logger.error("HTTP Exception: %s", str(e))
            raise e

        except Exception as e:
            logger.error("Unexpected Error processing NL to SQL request: %s", str(e), exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error processing NL to SQL request: {str(e)}"
            )