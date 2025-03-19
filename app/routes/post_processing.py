from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.models.pre_processing import ExternalDBModel, GeneratedQuery
from app.services.post_processing import execute_external_query
from app.core.db import get_db
from app.schemas import ExecuteQueryRequest

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

@router.get("/", response_model=list)
def get_queries_for_external_db(external_db_id: int, db: Session = Depends(get_db)):
    queries = db.query(GeneratedQuery).filter(GeneratedQuery.external_db_id == external_db_id).all()

    if not queries:
        raise HTTPException(status_code=404, detail="No queries found for the given external database")

    return [{"id": q.id, "query": q.query_text, "explanation": q.explanation} for q in queries]