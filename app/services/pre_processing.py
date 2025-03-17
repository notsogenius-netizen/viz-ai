import httpx
import asyncio
import json
from fastapi import HTTPException
from sqlalchemy.orm import Session
from app.models.pre_processing import ExternalDBModel, GeneratedQuery
from app.models.user import UserProjectRole, RoleModel
from app.utils.schema_structure import get_schema_structure
from app.utils.auth_dependencies import get_current_user
from app.schemas import ExternalDBCreateRequest, ExternalDBResponse, CurrentUser, UpdateDBRequest,NLQResponse, ExternalDBCreateChatRequest
from typing import List

async def create_or_update_external_db(data: ExternalDBCreateRequest, db: Session, current_user: CurrentUser):
    """
    Connects to the external database, retrieves schema, and saves it in the internal database.
    """

    try:
        user_id = current_user.user_id
        user_role = data.role
        print(data.role)

        # Check if UserProjectRole exists
        new_user_project_role = UserProjectRole(
            user_id = user_id,
            project_id = data.project_id,
            role_id = data.role
        )
        
        db.add(new_user_project_role)
        db.commit()
        db.refresh(new_user_project_role)

        if not new_user_project_role:
            raise HTTPException(status_code=400, detail="User does not have a role in this project.")

        # Retrieve schema structure
        schema_structure = get_schema_structure(data.connection_string)

        # Check if entry exists (Update case)
        db_entry = db.query(ExternalDBModel).filter_by(user_project_role_id= new_user_project_role.id).first()
        if db_entry:
            db_entry.connection_string = data.connection_string
            db_entry.domain = data.domain if data.domain else None
            db_entry.database_provider = data.db_type
            db_entry.schema_structure = json.dumps(schema_structure)
        else:
            db_entry = ExternalDBModel(
                user_project_role_id=new_user_project_role.id,
                connection_string=data.connection_string,
                domain=data.domain if data.domain else None,
                database_provider = data.db_type,
                schema_structure=json.dumps(schema_structure),
            )
            db.add(db_entry)

        db.commit()
        db.refresh(db_entry)
        
        schema_structure_string = json.dumps(schema_structure, indent=2)
        

        return ExternalDBResponse(
            # role= user_role,
            # domain= data.domain if data.domain else None,
            # db_schema= schema_structure_string,
            # api_key= data.api_key,
            # db_type= data.db_type,
            # min_date= schema_structure["min_date"],
            # max_date= schema_structure["max_date"]
            db_entry_id = db_entry.id
        )
    
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error processing external DB: {str(e)}")

async def update_record(data: UpdateDBRequest, db: Session, current_user: CurrentUser):
    """
        Updates the domain and sends the request to llm service.
    """

    try:
        user_id= current_user.user_id
        print(user_id, data.project_id)
        user_project_role = db.query(UserProjectRole).filter(
            UserProjectRole.user_id == user_id,
            UserProjectRole.project_id == data.project_id
        ).first()
        print(user_project_role.role_id)
        user_role_id = user_project_role.role_id
        
        user_role = db.query(RoleModel).filter(RoleModel.id == user_role_id).first().name
        print(data.db_entry_id)
        db_entry= db.query(ExternalDBModel).filter(ExternalDBModel.id == data.db_entry_id).first()

        if not db_entry:
            raise HTTPException(status_code=404, detail="Database entry not found.")

        schema_structure = db_entry.schema_structure
        db_provider = db_entry.database_provider
        min_date = db_entry.min_date
        max_date = db_entry.max_date

        db_entry.domain = data.domain

        db.commit()
        db.refresh(db_entry)

        return {
            "role": user_role,
            "db_schema": schema_structure,
            "db_type": db_provider,
            "domain": data.domain,
            "min_date": min_date,
            "max_date": max_date,
            "api_key": ""
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error updating record: {str(e)}")

async def save_query_to_db(queries, db: Session, db_entry_id: int):
    """
        Save the llm response to db.
    """
    saved_queries = []
    external_db = db.query(ExternalDBModel).filter(ExternalDBModel.id == db_entry_id).first()
    
    query_list = queries.get("queries", [])
    
    if not external_db:
        raise HTTPException(status_code=404, detail="External DB not found")
    for query_data in query_list:
        query_entry = GeneratedQuery(
            external_db_id=db_entry_id,
            query_text=query_data['query'],
            explanation=query_data["explanation"],
            relevance=query_data["relevance"],
            is_time_based=bool(query_data["is_time_based"]),
            chart_type=query_data["chart_type"],
        )
        db.add(query_entry)
        saved_queries.append(query_entry)

    db.commit()
    return {"status": "success", "message": "Queries saved successfully"}
# Add these functions to your app/services/pre_processing.py file

async def process_nl_to_sql_query(data: ExternalDBCreateChatRequest, db: Session, current_user: CurrentUser):
    try:
        user_id = current_user.user_id
        user_role = current_user.role

        user_project_roles = db.query(UserProjectRole).filter(
            UserProjectRole.user_id == user_id
        ).all()
        
        if not user_project_roles:
            raise HTTPException(status_code=400, detail="User does not have any project roles.")
        

        db_entry = None
        for upr in user_project_roles:
            db_entry = db.query(ExternalDBModel).filter_by(user_project_role_id=upr.id).first()
            if db_entry:
                break
                
        if not db_entry:
            raise HTTPException(status_code=404, detail="No database connections found for this user.")
        
        schema_structure = json.loads(db_entry.schema_structure)
        schema_structure_string = json.dumps(schema_structure, indent=2)
        
        nlq_request = {
            "nl_query": data.nl_query,
            "db_schema": schema_structure_string,
            "db_type": db_entry.database_provider,
            "api_key": data.api_key if hasattr(data, 'api_key') else None
        }
        
        return nlq_request, db_entry.id
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error processing NL to SQL request: {str(e)}")

async def save_nl_sql_query(sql_response, db: Session, db_entry_id):
    try:
        external_db = db.query(ExternalDBModel).filter(ExternalDBModel.id == db_entry_id).first()
        if not external_db:
            raise HTTPException(status_code=404, detail="External DB not found")
        
        if 'sql_query' in sql_response:
            new_query = GeneratedQuery(
                external_db_id=db_entry_id,
                query_text=sql_response['sql_query'],
                explanation=sql_response.get('explanation', 'Generated from natural language query'),
                relevance=1.0, 
                # is_time_based=False,  # You might want logic to detect this
                chart_type=sql_response.get('chart_type')  # Default chart type for NL queries
            )
            db.add(new_query)
            db.commit()
            
            return {"status": "success", "message": "SQL query saved successfully", "query_id": new_query.id}
        else:
            raise HTTPException(status_code=400, detail="No SQL query found in the response")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error saving SQL query: {str(e)}")


async def post_to_llm(url: str, data: dict):
    """
        Send a async post request to llm service.
    """

    async with httpx.AsyncClient(timeout= 45.0) as client:
        response = await client.post(url, json=data)
        response.raise_for_status()  # Raise error if response status is not 200
        return response.json()
    
async def post_to_nlq_llm(url:str, data:dict):
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(url,json=data)
        response.raise_for_status()
        return response.json()