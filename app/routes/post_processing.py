from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.models.pre_processing import ExternalDBModel, GeneratedQuery
from app.services.post_processing import execute_external_query
from app.core.db import get_db

router = APIRouter(prefix="/execute-query", tags=["External Database"])


@router.post("/{external_db_id}/{query_id}")
def execute_query(
    external_db_id: int, query_id: int, db: Session = Depends(get_db)
):
    # Fetch external database details
    external_db = db.query(ExternalDBModel).filter(ExternalDBModel.id == external_db_id).first()
    if not external_db:
        raise HTTPException(status_code=404, detail="External database not found")

    # Fetch generated query
    generated_query = db.query(GeneratedQuery).filter(GeneratedQuery.id == query_id).first()
    if not generated_query:
        raise HTTPException(status_code=404, detail="Query not found")

    # Execute query on the external database
    result = execute_external_query(external_db, generated_query.query_text)
    return {"query": generated_query.query_text, "result": result}