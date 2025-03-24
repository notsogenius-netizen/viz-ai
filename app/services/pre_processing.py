import httpx
import json
from urllib.parse import quote_plus, urlparse
from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session
from app.models.pre_processing import ExternalDBModel, GeneratedQuery
from app.models.user import UserProjectRole, RoleModel
from app.utils.schema_structure import get_schema_structure
from app.utils.crypt import encrypt_string, decrypt_string
from app.schemas import ExternalDBCreateRequest, ExternalDBResponse, CurrentUser, UpdateDBRequest,NLQResponse, ExternalDBCreateChatRequest
from datetime import datetime
from uuid import UUID
import logging

logger = logging.getLogger("app")

async def create_or_update_external_db(data: ExternalDBCreateRequest, db: Session, current_user: CurrentUser):
    user_id = current_user.user_id
    logger.info(f"User {user_id} is attempting to create or update an external DB for project {data.project_id}.")

    try:
        new_user_project_role = UserProjectRole(
            user_id=user_id,
            project_id=data.project_id,
            role_id=data.role
        )
        db.add(new_user_project_role)
        db.commit()
        db.refresh(new_user_project_role)
        logger.info(f"Assigned role {data.role} to user {user_id} for project {data.project_id}.")

        if not new_user_project_role:
            logger.warning(f"User {user_id} does not have a role in project {data.project_id}.")
            raise HTTPException(status_code=400, detail="User does not have a role in this project.")

        if data.connection_string:
            parsed_url = urlparse(data.connection_string)
            encoded_password = quote_plus(parsed_url.password) if parsed_url else ""
            connection_string = f"{parsed_url.scheme}://{parsed_url.username}:{encoded_password}@{parsed_url.hostname}{':' + str(parsed_url.port) if parsed_url.port else ''}{parsed_url.path}?{parsed_url.query}"
            schema_structure = get_schema_structure(connection_string, data.db_type)
            logger.info(f"Retrieved schema structure for database type {data.db_type}.")
        else:
            db_type = data.db_type.lower()
            username = data.name
            password = quote_plus(data.password)
            host = data.host
            db_name = data.db_name

            if db_type == "postgres":
                reconstructed_conn_string = f"postgresql://{username}:{password}@{host}/{db_name}"
                logger.debug(f"Reconstructed PostgreSQL connection string: {reconstructed_conn_string}")
                schema_structure = get_schema_structure(reconstructed_conn_string, db_type)
            elif db_type == "mysql":
                reconstructed_conn_string = f"mysql+pymysql://{username}:{password}@{host}/{db_name}"
                logger.debug(f"Reconstructed MySQL connection string: {reconstructed_conn_string}")
                schema_structure = get_schema_structure(reconstructed_conn_string, db_type)
            else:
                logger.error(f"Unsupported database type: {data.db_type}")
                raise HTTPException(status_code=400, detail="Unsupported database type.")

        db_entry = db.query(ExternalDBModel).filter_by(user_project_role_id=new_user_project_role.id).first()

        if db_entry:
            db_entry.connection_string = encrypt_string(data.connection_string)
            db_entry.domain = data.domain if data.domain else None
            db_entry.database_provider = data.db_type
            db_entry.schema_structure = json.dumps(schema_structure)
            db_entry.min_date = schema_structure["min_date"]
            db_entry.max_date = schema_structure["max_date"]
            logger.info(f"Updated existing external DB entry for user {user_id}.")
        else:
            db_entry = ExternalDBModel(
                user_project_role_id=new_user_project_role.id,
                connection_string=encrypt_string(data.connection_string),
                domain=data.domain if data.domain else None,
                database_provider=data.db_type,
                schema_structure=json.dumps(schema_structure),
                min_date=schema_structure["min_date"],
                max_date=schema_structure["max_date"]
            )
            db.add(db_entry)
            logger.info(f"Created new external DB entry for user {user_id}.")

        db.commit()
        db.refresh(db_entry)

        return ExternalDBResponse(
            db_entry_id=db_entry.id
        )

    except IntegrityError as e:
        db.rollback()
        logger.error(f"Database constraint violation: {str(e)}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Database constraint violation.")

    except HTTPException as http_exc:
        db.rollback()
        logger.error(f"HTTP exception occurred: {str(http_exc)}")
        raise http_exc

    except Exception as e:
        db.rollback()
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error processing external DB: {str(e)}")
    
async def update_record(data: UpdateDBRequest, db: Session, current_user: CurrentUser):
    """
    Updates the domain and sends the request to the LLM service.
    """
    try:
        user_id = current_user.user_id
        logger.debug(f"Updating record for user_id: {user_id}, project_id: {data.project_id}")

        user_project_role = db.query(UserProjectRole).filter(
            UserProjectRole.user_id == user_id,
            UserProjectRole.project_id == data.project_id
        ).first()

        if not user_project_role:
            logger.warning(f"No project role found for user_id: {user_id}, project_id: {data.project_id}")
            raise HTTPException(status_code=404, detail="User project role not found.")

        logger.debug(f"User project role ID: {user_project_role.role_id}")

        user_role = db.query(RoleModel).filter(RoleModel.id == user_project_role.role_id).first().name
        logger.debug(f"User role: {user_role}")

        db_entry = db.query(ExternalDBModel).filter(ExternalDBModel.id == data.db_entry_id).first()

        if not db_entry:
            logger.error(f"Database entry not found for db_entry_id: {data.db_entry_id}")
            raise HTTPException(status_code=404, detail="Database entry not found.")

        schema_structure = db_entry.schema_structure
        db_provider = db_entry.database_provider
        min_date = db_entry.min_date.isoformat() if isinstance(db_entry.min_date, datetime) else db_entry.min_date
        max_date = db_entry.max_date.isoformat() if isinstance(db_entry.max_date, datetime) else db_entry.max_date
        logger.debug(f"Schema structure: {schema_structure}")
        logger.debug(f"Database provider: {db_provider}")
        logger.debug(f"Min date: {min_date}, Max date: {max_date}")

        db_entry.domain = data.domain
        db.commit()
        db.refresh(db_entry)
        logger.info(f"Updated domain for db_entry_id: {data.db_entry_id} to {data.domain}")

        response = {
            "role": user_role,
            "db_schema": schema_structure,
            "db_type": db_provider,
            "domain": data.domain,
            "min_date": min_date,
            "max_date": max_date,
            "api_key": ""
        }
        return response

    except IntegrityError as e:
        db.rollback()
        logger.error(f"IntegrityError occurred: {str(e)}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Database constraint violation.")

    except HTTPException as http_exc:
        db.rollback()
        logger.error(f"HTTPException occurred: {http_exc.detail}")
        raise http_exc  # Re-raise known HTTP exceptions

    except Exception as e:
        db.rollback()
        logger.critical(f"Unexpected error occurred: {str(e)}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error updating record: {str(e)}")

async def save_query_to_db(queries: dict, db: Session, db_entry_id: int, user_id: UUID):
    """
    Save the LLM response to the database.
    """
    saved_queries = []
    try:
        logger.debug(f"Attempting to retrieve ExternalDBModel with id {db_entry_id}.")
        external_db = db.query(ExternalDBModel).filter(ExternalDBModel.id == db_entry_id).first()
        
        if not external_db:
            logger.warning(f"External DB with id {db_entry_id} not found.")
            raise HTTPException(status_code=404, detail="External DB not found")
        
        query_list = queries.get("queries", [])
        logger.info(f"Retrieved {len(query_list)} queries to save for db_entry_id {db_entry_id}.")

        for query_data in query_list:
            query_entry = GeneratedQuery(
                external_db_id=db_entry_id,
                user_id=user_id,
                query_text=query_data['query'],
                explanation=query_data["explanation"],
                relevance=query_data["relevance"],
                is_time_based=bool(query_data["is_time_based"]),
                chart_type=query_data["chart_type"],
                is_user_generated=False
            )
            db.add(query_entry)
            saved_queries.append(query_entry)
            logger.debug(f"Added query for user {user_id} to the session: {query_data['query']}.")

        db.commit()
        logger.info(f"Successfully committed {len(saved_queries)} queries to the database for db_entry_id {db_entry_id}.")
        return {"status": "success", "message": "Queries saved successfully", "queries": queries}

    except IntegrityError as ie:
        db.rollback()
        logger.error(f"IntegrityError while saving queries for db_entry_id {db_entry_id}: {str(ie)}")
        raise HTTPException(status_code=400, detail="Database constraint violation.")

    except HTTPException as http_exc:
        db.rollback()
        logger.error(f"HTTPException while saving queries for db_entry_id {db_entry_id}: {str(http_exc.detail)}")
        raise http_exc

    except Exception as e:
        db.rollback()
        logger.critical(f"Unexpected error while saving queries for db_entry_id {db_entry_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error saving queries: {str(e)}")
        
async def process_nl_to_sql_query(data: ExternalDBCreateChatRequest, db: Session, current_user: CurrentUser):
    """
    Processes a natural language query to generate an SQL query.

    Args:
        data (ExternalDBCreateChatRequest): The request data containing the NL query.
        db (Session): The database session.
        current_user (CurrentUser): The current authenticated user.

    Returns:
        Tuple containing the NLQ request dictionary and the database entry ID.
    """
    try:
        user_id = current_user.user_id
        logger.info("Processing NL to SQL query for user_id: %s", user_id)

        # Retrieve user project roles
        user_project_roles = db.query(UserProjectRole).filter(
            UserProjectRole.user_id == user_id
        ).all()
        logger.debug("Retrieved user project roles: %s", user_project_roles)

        if not user_project_roles:
            logger.warning("No project roles found for user_id: %s", user_id)
            raise HTTPException(status_code=400, detail="User does not have any project roles.")

        # Find the associated database entry
        db_entry = None
        for upr in user_project_roles:
            db_entry = db.query(ExternalDBModel).filter_by(user_project_role_id=upr.id).first()
            if db_entry:
                logger.debug("Found database entry: %s", db_entry)
                break

        if not db_entry:
            logger.error("No database connections found for user_id: %s", user_id)
            raise HTTPException(status_code=404, detail="No database connections found for this user.")

        # Parse the schema structure
        schema_structure = json.loads(db_entry.schema_structure)
        schema_structure_string = json.dumps(schema_structure, indent=2)
        logger.debug("Parsed schema structure: %s", schema_structure_string)

        # Prepare the NLQ request payload
        nlq_request = {
            "nl_query": data.nl_query,
            "db_schema": schema_structure_string,
            "db_type": db_entry.database_provider,
            "api_key": getattr(data, 'api_key', None)
        }
        logger.info("NLQ request prepared successfully for user_id: %s", user_id)

        return nlq_request, str(db_entry.id)

    except HTTPException as http_exc:
        logger.warning("HTTP exception occurred: %s", http_exc.detail)
        raise http_exc

    except Exception as e:
        logger.exception("Unexpected error processing NL to SQL request for user_id: %s", user_id)
        raise HTTPException(status_code=500, detail=f"Error processing NL to SQL request: {str(e)}")
    
async def save_nl_sql_query(sql_response: dict, db: Session, db_entry_id: int, user_id: UUID):
    """
    Save the generated SQL query from a natural language input into the database.

    Args:
        sql_response (dict): The response containing the SQL query and related information.
        db (Session): The database session.
        db_entry_id (int): The ID of the external database entry.
        user_id (UUID): The ID of the user.

    Returns:
        dict: A dictionary indicating the status and message of the operation.

    Raises:
        HTTPException: If the external database entry is not found or if an error occurs during the process.
    """
    try:
        logger.info("Attempting to save NL to SQL query for user_id: %s and db_entry_id: %s", user_id, db_entry_id)

        # Retrieve the external database entry
        external_db = db.query(ExternalDBModel).filter(ExternalDBModel.id == db_entry_id).first()
        if not external_db:
            logger.warning("External DB not found for db_entry_id: %s", db_entry_id)
            raise HTTPException(status_code=404, detail="External DB not found")

        # Check if 'sql_query' exists in the response
        if 'sql_query' in sql_response:
            # Create a new GeneratedQuery instance
            new_query = GeneratedQuery(
                user_id=user_id,
                external_db_id=db_entry_id,
                query_text=sql_response['sql_query'],
                explanation=sql_response.get('explanation', 'Generated from natural language query'),
                relevance=1.0,
                is_time_based=False,
                chart_type=sql_response.get('chart_type'),
                is_user_generated=True
            )
            db.add(new_query)
            db.commit()
            logger.info("SQL query saved successfully with query_id: %s", new_query.id)
            return {"status": "success", "message": "SQL query saved successfully", "query_id": str(new_query.id)}
        else:
            logger.warning("No SQL query found in the response for user_id: %s", user_id)
            raise HTTPException(status_code=400, detail="No SQL query found in the response")

    except HTTPException as http_exc:
        db.rollback()
        logger.error("HTTPException occurred: %s", http_exc.detail)
        raise http_exc

    except SQLAlchemyError as db_err:
        db.rollback()
        logger.exception("Database error occurred while saving NL to SQL query for user_id: %s", user_id)
        raise HTTPException(status_code=500, detail="Database error occurred. Please try again later.")

    except Exception as e:
        db.rollback()
        logger.exception("Unexpected error occurred while saving NL to SQL query for user_id: %s", user_id)
        raise HTTPException(status_code=500, detail=f"Error processing NL to SQL request: {str(e)}")

async def post_to_llm(url: str, data: dict):    
    """
    Send an async POST request to the LLM service.
    """
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(url, json=data)
            response.raise_for_status()  
            return response.json()

    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=f"LLM service returned an error: {e.response.text}")

    except httpx.RequestError as e:
        raise HTTPException(status_code=500, detail=f"Request to LLM service failed: {str(e)}")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")
    
async def post_to_nlq_llm(url:str, data:dict):
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url,json=data)
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=e.response.status_code,
            detail=f"NLQ LLM service returned an error: {e.response.text}"
        )

    except httpx.RequestError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Request to NLQ LLM service failed: {str(e)}"
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"An unexpected error occurred: {str(e)}"
        )