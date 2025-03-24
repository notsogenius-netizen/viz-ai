
from typing import Dict, Any, List, Tuple, Optional
import logging
import httpx
import json
from sqlalchemy import text
from app.models.pre_processing import ExternalDBModel,GeneratedQuery
from app.models.post_processing import Dashboard, DashboardQueryAssociation
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from fastapi import HTTPException
from app.utils.schema_structure import get_external_db_session
from app.utils.auth_dependencies import get_user_project_role
from app.schemas import TimeBasedQueriesUpdateRequest, TimeBasedQueriesUpdateResponse, QueryWithId
from uuid import UUID
from datetime import date

logger = logging.getLogger("app")

def execute_external_query(external_db: ExternalDBModel, query: str):
    """
    Executes a SQL query on the external database.

    :param external_db: ExternalDBModel instance with connection info.
    :param query: SQL query string.
    :return: Query results
    """
    session, engine = get_external_db_session(external_db)
    try:
        print(query)
        result = session.execute(text(query))
        data = result.fetchall()  # Fetch all results
        response = [dict(row._mapping) for row in data]  # Convert result to dictionary
        return transform_data_dynamic(response)
    except Exception as e:
        return {"error": str(e)}
    finally:
        session.close()  # Close session after use
        engine.dispose() 



def transform_data_dynamic(data):
    """
    Transforms an array of dictionaries into the required format by dynamically detecting fields.
    Also returns the detected x-axis and y-axis labels.

    :param data: List of dictionaries with unknown key names
    :return: Dictionary containing transformed data and axis labels
    """
    if not data:
        return {"data": [], "x_axis": None, "y_axis": None}

    keys = list(data[0].keys())

    if len(keys) < 2:
        raise ValueError("Data must contain at least two fields (one for label and one for value).")

    x_axis = keys[0]  # First key for x-axis
    y_axis = keys[1]  # Second key for y-axis

    transformed_data = [{"label": str(item[x_axis]), "value": item[y_axis]} for item in data]

    return {"data": transformed_data, "x_axis": x_axis, "y_axis": y_axis}

async def process_time_based_queries(
    db: Session,
    dashboard_id: str,
    min_date: str,
    max_date: str,
    api_key: str,
    llm_url: str
) -> TimeBasedQueriesUpdateResponse:
    try:
        dashboard_uuid = UUID(dashboard_id)

        dashboard = db.query(Dashboard).filter(Dashboard.id == dashboard_uuid).first()
        if not dashboard:
            raise HTTPException(status_code=404, detail="Dashboard not found.")

        external_db = db.query(ExternalDBModel).filter(ExternalDBModel.id == dashboard.external_db_id).first()
        if not external_db:
            raise HTTPException(status_code=404, detail="External database not found.")

        db_type = external_db.database_provider.lower()

        queries = db.query(GeneratedQuery).filter(
            GeneratedQuery.dashboards.any(id=dashboard_uuid),
            GeneratedQuery.is_time_based == True
        ).all()

        if not queries:
            raise HTTPException(status_code=404, detail="No time-based queries found for this dashboard.")

        query_list = [QueryWithId(query_id=str(q.id), query=q.query_text) for q in queries]

        min_date = min_date.isoformat() if isinstance(min_date, date) else str(min_date)
        max_date = max_date.isoformat() if isinstance(max_date, date) else str(max_date)

        request_data = TimeBasedQueriesUpdateRequest(
            queries=query_list,
            min_date=min_date,
            max_date=max_date,
            db_type=db_type  
        )

        logger.info(f"Sending JSON Payload to LLM: {json.dumps(request_data.model_dump(), indent=2)}")

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                llm_url,
                json=request_data.model_dump(),
            )
            try:
                response.raise_for_status()
                response_json = response.json()
                if not response_json:
                    raise ValueError("Empty response from LLM")
                logger.info(f"LLM Response: {json.dumps(response_json, indent=2)}")
            except Exception as e:
                logger.error(f"Failed to parse LLM response: {str(e)}")
                raise HTTPException(status_code=500, detail="Invalid response from LLM service.")

        updated_queries_response = TimeBasedQueriesUpdateResponse(**response_json)
        await update_queries_in_db(db, updated_queries_response.updated_queries)


        return updated_queries_response

    except HTTPException as e:
        logger.error(f"HTTP Exception: {e.detail}")
        raise e
    except httpx.HTTPStatusError as e:
        logger.error(f"LLM service error: {e.response.text}")
        raise HTTPException(status_code=500, detail=f"LLM service error: {e.response.text}")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing time-based queries: {str(e)}")


async def update_queries_in_db(db: Session, updated_queries):
    for updated_query in updated_queries:
        query_entry = db.query(GeneratedQuery).filter(GeneratedQuery.id == UUID(updated_query.query_id)).first()
        
        if query_entry:
            if updated_query.success:
                query_entry.query_text = updated_query.updated_query
                db.commit()
                db.refresh(query_entry)
                logger.info(f"Query {query_entry.id} updated successfully.")
            else:
                logger.error(f"Failed to update query {query_entry.id}: {updated_query.error}")

def get_paginated_queries(db: Session, user_id: str, external_db_id: str):
    try:
        logger.info(f"Fetching paginated queries for user_id={user_id}, external_db_id={external_db_id}")
        # Count already sent queries
        sent_count = (
            db.query(GeneratedQuery)
            .filter(
                GeneratedQuery.user_id == user_id,
                GeneratedQuery.external_db_id == external_db_id,
                GeneratedQuery.is_sent == True,
                GeneratedQuery.is_user_generated == False
            )
            .count()
        )
        logger.debug(f"Sent LLM-generated query count: {sent_count}")

        if sent_count >= 30:
            raise HTTPException(status_code=400, detail="No more reloads available.")

                
        if sent_count < 10:
            new_limit = 10
        elif sent_count < 20:
            new_limit = 10
        elif sent_count < 30:
            new_limit = 10
        else:
            new_limit = 0

        logger.debug(f"New queries limit: {new_limit}")

        # Fetch previously sent queries
        previously_sent_queries = (
            db.query(GeneratedQuery)
            .filter(
                GeneratedQuery.user_id == user_id,
                GeneratedQuery.external_db_id == external_db_id,
                GeneratedQuery.is_sent == True,
                GeneratedQuery.is_user_generated == False
            )
            .order_by(GeneratedQuery.created_at)
            .all()
        )

        # Fetch new queries to be sent now
        new_time_based_queries = (
            db.query(GeneratedQuery)
            .filter(
                GeneratedQuery.user_id == user_id,
                GeneratedQuery.external_db_id == external_db_id,
                GeneratedQuery.is_time_based == True,
                GeneratedQuery.is_sent == False,
                GeneratedQuery.is_user_generated == False,
            )
            .order_by(GeneratedQuery.created_at)
            .limit(new_limit // 2)  # Fetch half of the new limit
            .all()
        )

        new_non_time_based_queries = (
            db.query(GeneratedQuery)
            .filter(
                GeneratedQuery.user_id == user_id,
                GeneratedQuery.external_db_id == external_db_id,
                GeneratedQuery.is_time_based == False,
                GeneratedQuery.is_sent == False,
                GeneratedQuery.is_user_generated == False,
            )
            .order_by(GeneratedQuery.created_at)
            .limit(new_limit - len(new_time_based_queries))
            .all()
        )

        logger.debug(f"Fetched {len(new_time_based_queries)} time-based queries")
        logger.debug(f"Fetched {len(new_non_time_based_queries)} non-time-based queries")

        # Combine previously sent + new queries
        queries = previously_sent_queries + new_time_based_queries + new_non_time_based_queries

        # Mark only new queries as sent
        for query in new_time_based_queries + new_non_time_based_queries:
            query.is_sent = True

        db.commit()
        logger.info(f"Returning {len(queries)} queries for user_id={user_id}")

        return queries

    except HTTPException as e:
        logger.warning(f"HTTPException: {e.detail}")
        raise

    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Database error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Database error occurred.")

    except Exception as e:
        db.rollback()
        logger.critical(f"Unexpected error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="An unexpected error occurred.")
    
def create_or_get_dashboard(db: Session, name: str, external_db_id: UUID, user_id: UUID, role_id: UUID):
    """
    Retrieve an existing dashboard or create a new one with the given name.
    """
    try:
        user_project_role = get_user_project_role(db, user_id, role_id)

        dashboard = (
            db.query(Dashboard)
            .filter(Dashboard.user_project_role_id == user_project_role.id, Dashboard.name == name)
            .first()
        )

        if not dashboard:
            dashboard = Dashboard(
                name=name,
                external_db_id=external_db_id,
                user_project_role_id=user_project_role.id
            )
            db.add(dashboard)
            db.commit()
            db.refresh(dashboard)

        return dashboard
    except SQLAlchemyError as e:  # Catch database-related errors
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

    except Exception as e:  # Catch any unexpected errors
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

def add_queries_to_dashboard(db: Session, dashboard: Dashboard, query_ids: list[UUID]):
    """
    Add selected queries to the given dashboard.
    """
    try:
        queries = db.query(GeneratedQuery).filter(GeneratedQuery.id.in_(query_ids)).all()

        if not queries:
            raise HTTPException(status_code=400, detail="No valid queries found.")
        
        existing_associations = {
            (assoc.dashboard_id, assoc.query_id)
            for assoc in db.query(DashboardQueryAssociation)
            .filter(DashboardQueryAssociation.dashboard_id == dashboard.id)
            .all()
        }

        new_associations = []
        for query in queries:
            if (dashboard.id, query.id) not in existing_associations:
                new_associations.append(DashboardQueryAssociation(dashboard_id=dashboard.id, query_id=query.id))

        if new_associations:
            db.add_all(new_associations)
            db.commit()
        return queries
    except SQLAlchemyError as e:  # Handle database-related errors
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

    except Exception as e:  # Catch any unexpected errors
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

def fetch_dashboard_chart_data(db: Session, dashboard_id: UUID):
    """
    Fetch queries for a given dashboard, execute them, and return the results.
    """
    try:
        # 🔹 Fetch the dashboard
        dashboard = db.query(Dashboard).filter(Dashboard.id == dashboard_id).first()
        if not dashboard:
            raise HTTPException(status_code=404, detail="Dashboard not found.")

        # 🔹 Fetch related queries
        queries = dashboard.queries
        if not queries:
            raise HTTPException(status_code=400, detail="No queries found for this dashboard.")

        # 🔹 Execute Queries and Collect Results
        chart_data = []
        for query in queries:
            external_db = db.query(ExternalDBModel).filter(ExternalDBModel.id == dashboard.external_db_id).first()
            if not external_db:
                raise HTTPException(status_code=400, detail="External database not found.")

            try:
                # Execute the query on the external DB
                result = execute_external_query(external_db, query.query_text)
                chart_data.append({
                    "query_id": str(query.id),
                    "query_text": query.explanation,
                    "result": result["data"],
                    "x_axis": result["x_axis"],
                    "y_axis": result["y_axis"],
                    "chart_type": query.chart_type
                })
            except Exception as e:
                logger.error(f"Query execution failed for query {query.id}: {str(e)}")
                continue 

        return {
            "dashboard_id": str(dashboard.id),
            "chart_data": chart_data
        }

    except HTTPException as e:
        logger.warning(f"Dashboard Fetch Warning: {e.detail}")
        raise
    except Exception as e:
        logger.exception(f"Unexpected error in fetch_dashboard_chart_data for dashboard {dashboard_id}")
        raise HTTPException(status_code=500, detail="Error fetching chart data.")
    
def remove_queries_from_dashboard(db: Session, dashboard_id: UUID, query_ids: list[UUID]):
    """
    Remove specified queries from a dashboard.
    """
    try:
        # Fetch the dashboard
        dashboard = db.query(Dashboard).filter(Dashboard.id == dashboard_id).first()
        if not dashboard:
            raise HTTPException(status_code=404, detail="Dashboard not found.")

        # Remove queries
        queries_to_remove = [query for query in dashboard.queries if query.id in query_ids]
        if not queries_to_remove:
            raise HTTPException(status_code=400, detail="No valid queries found to remove.")

        for query in queries_to_remove:
            dashboard.queries.remove(query)

        db.commit()
        return queries_to_remove

    except HTTPException as e:
        logger.warning(f"Dashboard Query Removal Warning: {e.detail}")
        raise
    except Exception as e:
        logger.exception(f"Unexpected error in remove_queries_from_dashboard for dashboard {dashboard_id}")
        raise HTTPException(status_code=500, detail="Error removing queries.")
    
def delete_dashboard(db: Session, dashboard_id: UUID):
    """
    Delete a dashboard and all associated queries.
    """
    try:
        # Fetch the dashboard
        dashboard = db.query(Dashboard).filter(Dashboard.id == dashboard_id).first()
        if not dashboard:
            raise HTTPException(status_code=404, detail="Dashboard not found.")

        # Remove all queries from the dashboard
        dashboard.queries.clear()
        db.delete(dashboard)
        db.commit()

    except HTTPException as e:
        logger.warning(f"Dashboard Deletion Warning: {e.detail}")
        raise
    except Exception as e:
        logger.exception(f"Unexpected error in delete_dashboard for dashboard {dashboard_id}")
        raise HTTPException(status_code=500, detail="Error deleting dashboard.")
