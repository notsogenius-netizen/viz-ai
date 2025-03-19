from sqlalchemy import text
from app.models.pre_processing import ExternalDBModel
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