from sqlalchemy import text
from app.models.pre_processing import ExternalDBModel
from app.utils.schema_structure import get_external_db_session

def execute_external_query(external_db: ExternalDBModel, query: str):
    """
    Executes a SQL query on the external database.

    :param external_db: ExternalDBModel instance with connection info.
    :param query: SQL query string.
    :return: Query results
    """
    session, engine = get_external_db_session(external_db)
    try:
        result = session.execute(text(query))
        data = result.fetchall()  # Fetch all results
        return [dict(row._mapping) for row in data]  # Convert result to dictionary
    except Exception as e:
        return {"error": str(e)}
    finally:
        session.close()  # Close session after use
        engine.dispose() 