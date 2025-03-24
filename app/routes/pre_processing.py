import httpx
import logging
from fastapi import APIRouter, Depends, HTTPException, status,Body
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.schemas import ExternalDBCreateRequest, ExternalDBResponse, CurrentUser, UpdateDBRequest,ExternalDBCreateChatRequest
from app.services.pre_processing import create_or_update_external_db, update_record, post_to_llm, save_query_to_db
from app.services.pre_processing import process_nl_to_sql_query,post_to_nlq_llm,save_nl_sql_query
from app.utils.auth_dependencies import get_current_user
from app.core.db import get_db
from app.core.settings import settings

router = APIRouter(prefix="/external-db", tags=["External Database"])

logger = logging.getLogger("app")


@router.post("/", response_model=ExternalDBResponse, status_code=status.HTTP_201_CREATED)
async def create_external_db(
    data: ExternalDBCreateRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user)
):
    """
    API to connect to an external database, retrieve schema, and store it in the internal database.
    """
    logger.info("Initiating external DB creation for user: %s", current_user.user_id)
    try:
        result = await create_or_update_external_db(data, db, current_user)
        logger.info("Successfully created/updated external DB for user: %s", current_user.user_id)
        return result
    except IntegrityError:
        db.rollback()
        logger.warning("Database constraint violation during external DB creation for user: %s", current_user.user_id)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Database constraint violation.")
    except HTTPException as http_exc:
        db.rollback()
        logger.error("HTTP exception during external DB creation for user: %s - %s", current_user.user_id, str(http_exc))
        raise http_exc
    except Exception as e:
        db.rollback()
        logger.exception("Unexpected error during external DB creation for user: %s", current_user.user_id)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error processing external DB: {str(e)}")

@router.patch("/", status_code=status.HTTP_202_ACCEPTED)
async def update_record_and_call_llm(
    data: UpdateDBRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user)
):
    """
    API to update external DB model and call LLM service for processing.
    """
    logger.info("Updating record and calling LLM for user: %s", current_user.user_id)
    base_uri = "http://192.168.1.5:8000"
    url = f"{base_uri}/queries/"
    try:
        saved_data = await update_record(data, db, current_user)
        logger.debug("Record updated successfully for user: %s, data: %s", current_user.user_id, saved_data)
        llm_response = await post_to_llm(url, saved_data)
        logger.debug("Received response from LLM for user: %s, response: %s", current_user.user_id, llm_response)
        response = await save_query_to_db(queries=llm_response, db=db, db_entry_id=data.db_entry_id, user_id=current_user.user_id)
        logger.info("Successfully saved LLM query to DB for user: %s", current_user.user_id)
        return response
    except httpx.HTTPStatusError as e:
        logger.error("LLM service returned an error for user: %s - %s", current_user.user_id, e.response.text)
        raise HTTPException(status_code=e.response.status_code, detail=f"LLM service returned an error: {e.response.text}")
    except httpx.RequestError as e:
        logger.error("Request to LLM service failed for user: %s - %s", current_user.user_id, str(e))
        raise HTTPException(status_code=500, detail=f"Request to LLM service failed: {str(e)}")
    except ValueError as e:
        logger.warning("Invalid data error for user: %s - %s", current_user.user_id, str(e))
        raise HTTPException(status_code=400, detail=f"Invalid data error: {str(e)}")
    except Exception as e:
        logger.exception("Unexpected error during record update and LLM call for user: %s", current_user.user_id)
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")

@router.post("/nl-to-sql", status_code=status.HTTP_200_OK)
async def convert_nl_to_sql(data: ExternalDBCreateChatRequest = Body(...), db: Session = Depends(get_db), current_user: CurrentUser = Depends(get_current_user)):
        base_uri = "http://192.168.1.5:8000"

        url = f"{base_uri}/api/nlq/convert_nl_to_sql"
        print("Recivied data",data)
        user_id = current_user.user_id
        try:              
            logger.info("Received NL query: %s", data.nl_query)
            nlq_data, db_entry_id = await process_nl_to_sql_query(data, db, current_user)
            logger.info("Processed NL to SQL Query, Data: %s, DB Entry ID: %s", nlq_data, db_entry_id)
            sql_response = await post_to_nlq_llm(url, nlq_data)
            # logger.info("Received SQL response: %s", sql_response)

            save_result = await save_nl_sql_query(sql_response, db, db_entry_id, user_id)        
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