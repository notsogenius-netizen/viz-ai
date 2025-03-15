import httpx
import asyncio
import json
from fastapi import HTTPException
from sqlalchemy.orm import Session
from app.models.pre_processing import ExternalDBModel, GeneratedQuery
from app.models.user import UserProjectRole
from app.utils.schema_structure import get_schema_structure
from app.utils.auth_dependencies import get_current_user
from app.schemas import ExternalDBCreateRequest, ExternalDBResponse, CurrentUser, UpdateDBRequest

async def create_or_update_external_db(data: ExternalDBCreateRequest, db: Session, current_user: CurrentUser):
    """
    Connects to the external database, retrieves schema, and saves it in the internal database.
    """

    try:
        user_id = current_user.user_id
        user_role = current_user.role

        # Check if UserProjectRole exists
        user_project_role = db.query(UserProjectRole).filter(
            UserProjectRole.user_id == user_id,
            UserProjectRole.project_id == data.project_id
        ).first()
        if not user_project_role:
            raise HTTPException(status_code=400, detail="User does not have a role in this project.")

        # Retrieve schema structure
        schema_structure = get_schema_structure(data.connection_string)

        # Check if entry exists (Update case)
        db_entry = db.query(ExternalDBModel).filter_by(user_project_role_id= user_project_role.id).first()
        if db_entry:
            db_entry.connection_string = data.connection_string
            db_entry.domain = data.domain
            db_entry.schema_structure = json.dumps(schema_structure)
        else:
            db_entry = ExternalDBModel(
                user_project_role_id=user_project_role.id,
                connection_string=data.connection_string,
                domain=data.domain,
                schema_structure=json.dumps(schema_structure),
            )
            db.add(db_entry)

        db.commit()
        db.refresh(db_entry)
        
        schema_structure_string = json.dumps(schema_structure, indent=2)
        

        return ExternalDBResponse(
            role= user_role,
            domain= data.domain if data.domain else None,
            db_schema= schema_structure_string,
            api_key= data.api_key,
            db_type= data.db_type,
            min_date= schema_structure["min_date"],
            max_date= schema_structure["max_date"]
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error processing external DB: {str(e)}")

async def update_record(data: UpdateDBRequest, db: Session, current_user: CurrentUser):
    """
        Updates the domain and sends the request to llm service.
    """

    try:
        user_role= current_user.role

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

async def save_query_to_db(data, db: Session, db_entry_id):
    """
        Save the llm response to db.
    """

    external_db = db.query(ExternalDBModel).filter(ExternalDBModel.id == db_entry_id).first()
    if not external_db:
        raise HTTPException(status_code=404, detail="External DB not found")
    for query in data.queries:
        new_query = GeneratedQuery(
            external_db_id= db_entry_id,
            query_text=query.query,
            explanation=query.explanation,
            relevance=query.relevance,
            is_time_based=query.is_time_based,
            chart_type=query.chart_type
        )
        db.add(new_query)

    db.commit()
    return {"status": "success", "message": "Queries saved successfully"}

async def post_to_llm(url: str, data: dict):
    async with httpx.AsyncClient(timeout= 45.0) as client:
        response = await client.post(url, json=data)
        response.raise_for_status()  # Raise error if response status is not 200
        return response.json()