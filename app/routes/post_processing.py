from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from app.models.pre_processing import ExternalDBModel, GeneratedQuery
from app.models.post_processing import Dashboard
from app.services.post_processing import process_time_based_queries,execute_external_query, get_paginated_queries
from app.core.db import get_db
from app.utils.auth_dependencies import get_current_user
from app.schemas import ExecuteQueryRequest,TimeBasedUpdateRequest,TimeBasedQueriesUpdateResponse,DashboardSchema, CurrentUser, CreateDefaultDashboardRequest
import logging
from app.core.settings import settings




router = APIRouter(prefix="/execute-query", tags=["External Database"])


@router.post("/")
def execute_query(
    data: ExecuteQueryRequest, db: Session = Depends(get_db)
):
    print(data)
    external_db = db.query(ExternalDBModel).filter(ExternalDBModel.id == data.external_db_id).first()
    if not external_db:
        raise HTTPException(status_code=404, detail="External database not found")

    generated_query = db.query(GeneratedQuery).filter(GeneratedQuery.id == data.query_id).first()
    if not generated_query:
        raise HTTPException(status_code=404, detail="Query not found")

    result = execute_external_query(external_db, generated_query.query_text)
    return {
        "result": result,
        "id": generated_query.id,
        "chartType": generated_query.chart_type,
        "report": generated_query.explanation
        }

@router.get("/")
def get_existing_or_initial_queries(
    external_db_id: str, 
    db: Session = Depends(get_db), 
    current_user: CurrentUser = Depends(get_current_user)
):
    """Fetch already sent queries. If none exist (first visit), load initial 10 queries."""
    user_id = current_user.user_id

    # Check if any queries were already sent
    sent_queries = (
        db.query(GeneratedQuery)
        .filter(
            GeneratedQuery.user_id == user_id,
            GeneratedQuery.external_db_id == external_db_id,
            GeneratedQuery.is_sent == True
        )
        .order_by(GeneratedQuery.created_at)
        .all()
    )

    if sent_queries:
        # If queries were already sent, return them
        return {"count": len(sent_queries), "queries_list": sent_queries}

    # If no queries were sent (first visit), load first 10 queries
    first_queries = get_paginated_queries(db, user_id, external_db_id)

    if not first_queries:
        raise HTTPException(status_code=400, detail="No queries available.")
    
    for query in first_queries:
        print(query.is_time_based)

    return {"count": len(first_queries), "queries_list": first_queries}

@router.get("/load-more")
def load_more_queries(external_db_id: str, db: Session = Depends(get_db), current_user: CurrentUser = Depends(get_current_user)):
    user_id = current_user.user_id
    try:
        queries = get_paginated_queries(db, user_id, external_db_id)
        count = 0
        for query in queries:
            count += 1
            q = query.is_time_based
        
        return {
            "count": count,
            "queries_list": queries
            }
    except HTTPException as e:
        raise e
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error fetching queries: {str(e)}")
    
@router.post("/update-time-based", response_model=TimeBasedQueriesUpdateResponse)
async def update_dashboard_queries(request_data: TimeBasedUpdateRequest, db: Session = Depends(get_db)):
    try:
        updated_queries_response = await process_time_based_queries(
            db=db,
            dashboard_id = request_data.dashboard_id,
            min_date = request_data.min_date,
            max_date = request_data.max_date,
            api_key = '',
            llm_url = settings.LLM_URI
        )
        return updated_queries_response

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating queries: {str(e)}")
    


@router.get("/get-dashboards", response_model=list[DashboardSchema])
def fetch_user_dashboards(user_id: str, external_db_id: int, db: Session = Depends(get_db)):
    dashboards = db.query(Dashboard).filter(
        Dashboard.user_project_role_id == user_id,
        Dashboard.external_db_id == external_db_id  
    ).all()

    if not dashboards:
        raise HTTPException(status_code=404, detail="No dashboards found for this user and external database.")

    return [{"dashboard_id": d.id, "dashboard_name": d.name} for d in dashboards]

@router.post("/create-default-dashboard")
def create_default_dashboard(data: CreateDefaultDashboardRequest, db: Session = Depends(get_db), current_user: CurrentUser = Depends(get_current_user)):
    pass
