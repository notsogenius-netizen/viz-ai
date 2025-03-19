from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from app.models.pre_processing import ExternalDBModel, GeneratedQuery
from app.services.post_processing import execute_external_query, get_paginated_queries
from app.core.db import get_db
from app.utils.auth_dependencies import get_current_user
from app.schemas import ExecuteQueryRequest, CurrentUser

router = APIRouter(prefix="/execute-query", tags=["External Database"])


@router.post("/")
def execute_query(
    data: ExecuteQueryRequest, db: Session = Depends(get_db)
):
    print(data)
    # Fetch external database details
    external_db = db.query(ExternalDBModel).filter(ExternalDBModel.id == data.external_db_id).first()
    if not external_db:
        raise HTTPException(status_code=404, detail="External database not found")

    # Fetch generated query
    generated_query = db.query(GeneratedQuery).filter(GeneratedQuery.id == data.query_id).first()
    if not generated_query:
        raise HTTPException(status_code=404, detail="Query not found")

    # Execute query on the external database
    result = execute_external_query(external_db, generated_query.query_text)
    return {
        "result": result,
        "id": generated_query.id,
        "chartType": generated_query.chart_type,
        "report": generated_query.explanation
        }

@router.get("/")
def fetch_queries(external_db_id: int, db: Session = Depends(get_db), current_user: CurrentUser = Depends(get_current_user)):
    user_id = current_user.user_id
    try:
        queries = get_paginated_queries(db, user_id, external_db_id)
        return queries
    except HTTPException as e:
        raise e
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error fetching queries: {str(e)}")