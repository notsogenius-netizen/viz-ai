import json
from typing import Dict, Any, List, Tuple, Optional
import json
import asyncio
import logging
import httpx
from sqlalchemy import text
from app.models.pre_processing import ExternalDBModel,GeneratedQuery
from app.models.post_processing import Dashboard
from app.utils.schema_structure import get_external_db_session
from app.schemas import TimeBasedQueriesUpdateRequest, TimeBasedQueriesUpdateResponse, QueryWithId
import httpx
from sqlalchemy.orm import Session
from fastapi import HTTPException


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
    
    :param data: List of dictionaries with unknown key names
    :return: List of transformed dictionaries
    """
    if not data:
        return []

    # Get the field names dynamically from the first record
    keys = list(data[0].keys())

    if len(keys) < 2:
        raise ValueError("Data must contain at least two fields (one for label and one for value).")

    # Assume the first column is the label and the second column is the value
    label_field = keys[0]   # Example: "date", "year_month"
    value_field = keys[1]   # Example: "amount", "total"

    return [{"label": str(item[label_field]), "value": item[value_field]} for item in data]


logger = logging.getLogger(__name__)

async def process_time_based_queries(
    db: Session,
    dashboard_id: int,
    min_date: str,
    max_date: str,
    api_key: str,
    llm_url: str
) -> TimeBasedQueriesUpdateResponse:
    try:
        dashboard = db.query(Dashboard).filter(Dashboard.id == dashboard_id).first()
        if not dashboard:
            raise HTTPException(status_code=404, detail="Dashboard not found.")

        external_db = db.query(ExternalDBModel).filter(ExternalDBModel.id == dashboard.external_db_id).first()
        if not external_db:
            raise HTTPException(status_code=404, detail="External database not found.")

        db_type = external_db.database_provider.lower()  # Set DB type dynamically
        queries = db.query(GeneratedQuery).filter(
            GeneratedQuery.dashboards.any(id=dashboard_id),
            GeneratedQuery.is_time_based == True
        ).all()

        if not queries:
            raise HTTPException(status_code=404, detail="No time-based queries found for this dashboard.")

        query_list = [QueryWithId(query_id=str(q.id), query=q.query_text) for q in queries]
        request_data = TimeBasedQueriesUpdateRequest(
            queries=query_list,
            min_date=min_date,
            max_date=max_date,
            db_type=db_type  
        )

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(llm_url, json=request_data.dict(), headers={"Authorization": f"Bearer {api_key}"})
            response.raise_for_status()
            updated_queries_response = TimeBasedQueriesUpdateResponse(**response.json())

        for updated_query in updated_queries_response.updated_queries:
            query_entry = db.query(GeneratedQuery).filter(GeneratedQuery.id == int(updated_query.query_id)).first()

            if query_entry:
                if updated_query.success:
                    query_entry.query_text = updated_query.updated_query
                    logger.info(f"Updated query {query_entry.id} successfully.")
                else:
                    logger.error(f"Failed to update query {query_entry.id}: {updated_query.error}")
        db.commit()

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
        query_entry = db.query(GeneratedQuery).filter(GeneratedQuery.id == int(updated_query.query_id)).first()
        
        if query_entry:
            if updated_query.success:
                query_entry.query_text = updated_query.updated_query
                db.commit()
                db.refresh(query_entry)
                logger.info(f"Updated query {query_entry.id} successfully.")
            else:
                logger.error(f"Failed to update query {query_entry.id}: {updated_query.error}")