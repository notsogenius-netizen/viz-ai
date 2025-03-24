from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from app.models.pre_processing import ExternalDBModel, GeneratedQuery
from app.models.post_processing import Dashboard
from app.services.post_processing import process_time_based_queries,execute_external_query, get_paginated_queries, create_or_get_dashboard, add_queries_to_dashboard, fetch_dashboard_chart_data, remove_queries_from_dashboard, delete_dashboard
from app.core.db import get_db
from app.utils.auth_dependencies import get_current_user, get_user_project_role
from app.schemas import ExecuteQueryRequest,TimeBasedUpdateRequest,TimeBasedQueriesUpdateResponse,DashboardSchema, CurrentUser, CreateDefaultDashboardRequest, AddQueriesToDashboardRequest, DashboardResponse, DashboardQueryDeleteRequest
import logging
from app.core.settings import settings
from typing import List
from uuid import UUID
import json



router = APIRouter(prefix="/execute-query", tags=["External Database"])

logger = logging.getLogger("app")

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
        "result": result["data"],
        "x_axis": result["x_axis"],
        "y_axis": result["y_axis"],
        "id": generated_query.id,
        "chartType": generated_query.chart_type,
        "report": generated_query.explanation
        }

@router.get("/")
def get_existing_or_initial_queries(
    external_db_id: UUID, 
    db: Session = Depends(get_db), 
    current_user: CurrentUser = Depends(get_current_user)
):
    """
    Fetch already sent queries. If none exist (first visit), load initial 10 queries.
    """
    user_id = current_user.user_id

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

    user_generated = db.query(GeneratedQuery).filter(
        GeneratedQuery.user_id == user_id,
        GeneratedQuery.external_db_id == external_db_id,
        GeneratedQuery.is_user_generated == True
    ).order_by(GeneratedQuery.created_at).all()

    llm_generated = [query for query in sent_queries if not query.is_user_generated]
    
    if not sent_queries:
        initial_queries = get_paginated_queries(db, user_id, external_db_id)

        if not initial_queries:
            raise HTTPException(status_code=400, detail="No queries available.")

        llm_generated = initial_queries

    return {
        "queries_list": llm_generated,
        "user_generated": user_generated
    }

@router.get("/load-more")
def load_more_queries(external_db_id: str, db: Session = Depends(get_db), current_user: CurrentUser = Depends(get_current_user)):
    user_id = current_user.user_id
    try:
        queries = get_paginated_queries(db, user_id, external_db_id)
        count = 0
        for query in queries:
            count += 1
            print(query.explanation)
        
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
        llm_base_url = "http://192.168.1.5:8000"  
        llm_url = f"{llm_base_url}/update_time_based_queries/"
        
        updated_queries_response = await process_time_based_queries(
            db=db,
            dashboard_id=str(request_data.dashboard_id),
            min_date=request_data.min_date,
            max_date=request_data.max_date,
            api_key="",  
            llm_url=llm_url
        )

        return updated_queries_response

    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating queries: {str(e)}")


@router.post("/create-dashboard")
def create_dashboard(data: CreateDefaultDashboardRequest, db: Session = Depends(get_db), current_user: CurrentUser = Depends(get_current_user)):
    """
    Create or update a dashboard for the user with selected queries.
    If no name is provided, the default name is "Main Dashboard".
    """
    try:
        user_id = current_user.user_id
        role_id = data.role_id
        dashboard_name = data.name if data.name else "Untitled Dashboard"

        dashboard = create_or_get_dashboard(db, dashboard_name, data.db_entry_id, user_id, role_id)

        return {
            "message": "Dashboard created successfully",
            "dashboard_id": str(dashboard.id),
        }
    except HTTPException as e:
        raise e

    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")
    
@router.patch("/add-queries-to-dashboard")
def add_queries_to_dashboard_endpoint(data: AddQueriesToDashboardRequest, db: Session = Depends(get_db), current_user: CurrentUser = Depends(get_current_user)):
    """
    Add queries to an existing dashboard.
    """
    try:
        dashboard = db.query(Dashboard).filter(Dashboard.id == data.dashboard_id).first()
        if not dashboard:
            raise HTTPException(status_code=404, detail="Dashboard not found.")
        
        if data.name:
                dashboard.name = data.name
        
        queries_added = add_queries_to_dashboard(db, dashboard, data.query_ids)

        db.commit()

        return {
            "message": "Queries added successfully",
            "dashboard_id": str(dashboard.id),
            "queries_added": len(queries_added)
        }
    except HTTPException as e:
        raise e 

    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

@router.get("/dashboards", response_model=List[DashboardResponse])
def get_user_dashboards(
    role_id: UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    Fetch all dashboards for the current user with a specific role.
    """
    try:
        user_id = current_user.user_id

        # Fetch user_project_role
        user_project_role = get_user_project_role(db, user_id, role_id)

        if not user_project_role:
            raise HTTPException(status_code=404, detail="User project role not found.")

        # Fetch dashboards linked to the user_project_role
        dashboards = db.query(Dashboard).filter(
            Dashboard.user_project_role_id == user_project_role.id
        ).all()

        if not dashboards:
            raise HTTPException(status_code=404, detail="No dashboards found.")

        return dashboards

    except HTTPException as e:
        raise e

    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")
    
@router.get("/dashboard/chart-data")
def get_dashboard_chart_data(
    dashboard_id: UUID, 
    db: Session = Depends(get_db), 
    current_user=Depends(get_current_user)
):
    """
    Fetch chart data for a given dashboard.
    """
    try:
        return fetch_dashboard_chart_data(db, dashboard_id)
    except HTTPException as e:
        logger.error(f"HTTP Error: {e.detail}")
        raise
    except Exception as e:
        logger.exception(f"Unexpected error while fetching chart data for dashboard {dashboard_id}")
        raise HTTPException(status_code=500, detail="Internal server error.")
    
@router.delete("/dashboard/delete-queries")
def remove_queries(
    data: DashboardQueryDeleteRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """
    Remove specific queries from a dashboard.
    """
    try:
        removed_queries = remove_queries_from_dashboard(db, data.dashboard_id, data.query_ids)
        return {
            "message": "Queries removed successfully",
            "dashboard_id": str(data.dashboard_id),
            "queries_removed": len(removed_queries)
        }
    except HTTPException as e:
        logger.error(f"HTTP Error: {e.detail}")
        raise
    except Exception as e:
        logger.exception(f"Unexpected error while removing queries from dashboard {data.dashboard_id}")
        raise HTTPException(status_code=500, detail="Internal server error.")
    
@router.delete("/dashboard")
def delete_dashboard_endpoint(
    dashboard_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """
    Delete a dashboard and all associated queries.
    """
    try:
        delete_dashboard(db, dashboard_id)
        return {"message": "Dashboard deleted successfully", "dashboard_id": str(dashboard_id)}
    except HTTPException as e:
        logger.error(f"HTTP Error: {e.detail}")
        raise
    except Exception as e:
        logger.exception(f"Unexpected error while deleting dashboard {dashboard_id}")
        raise HTTPException(status_code=500, detail="Internal server error.")