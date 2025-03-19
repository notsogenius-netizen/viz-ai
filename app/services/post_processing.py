from sqlalchemy import text
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from fastapi import HTTPException
from app.models.pre_processing import ExternalDBModel, GeneratedQuery
from app.utils.schema_structure import get_external_db_session
import json

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


def get_paginated_queries(db: Session, user_id: int, external_db_id: int, limit: int = 10):
    try:
        # Count how many queries have already been sent
        sent_count = (
            db.query(GeneratedQuery)
            .filter(
                GeneratedQuery.user_id == user_id,
                GeneratedQuery.external_db_id == external_db_id,
                GeneratedQuery.is_sent == True
            )
            .count()
        )

        if sent_count >= 30:
            raise HTTPException(status_code=400, detail="No more reloads available.")

        # Fetch unsent queries first
        queries = (
            db.query(GeneratedQuery)
            .filter(
                GeneratedQuery.user_id == user_id,
                GeneratedQuery.external_db_id == external_db_id
            )
            .order_by(GeneratedQuery.is_sent, GeneratedQuery.created_at)
            .limit(limit)
            .all()
        )

        # Mark fetched queries as sent
        for query in queries:
            query.is_sent = True

        db.commit()

        return queries
    
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(status_code= 500, detail= f"Database error: {str(e)}")
