import logging
from sqlalchemy import text
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from fastapi import HTTPException
from app.models.pre_processing import ExternalDBModel, GeneratedQuery
from app.utils.schema_structure import get_external_db_session

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


def get_paginated_queries(db: Session, user_id: str, external_db_id: str):
    try:
        logger.info(f"Fetching paginated queries for user_id={user_id}, external_db_id={external_db_id}")
        # Count already sent queries
        sent_count = (
            db.query(GeneratedQuery)
            .filter(
                GeneratedQuery.user_id == user_id,
                GeneratedQuery.external_db_id == external_db_id,
                GeneratedQuery.is_sent == True
            )
            .count()
        )
        logger.debug(f"Sent query count: {sent_count}")

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
                GeneratedQuery.is_sent == True
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
                GeneratedQuery.is_sent == False
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
                GeneratedQuery.is_sent == False
            )
            .order_by(GeneratedQuery.created_at)
            .limit(new_limit - len(new_time_based_queries))  # Fill the remaining slots
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