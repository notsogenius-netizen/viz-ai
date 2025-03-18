from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker
from app.models.pre_processing import ExternalDBModel
from datetime import datetime, date

def get_schema_structure(connection_string: str, db_type: str):
    engine = create_engine(connection_string)
    inspector = inspect(engine)

    schema_info = {"tables": []}
    min_date, max_date = None, None

    try:
        with engine.connect() as connection:
            for table_name in inspector.get_table_names():
                columns = inspector.get_columns(table_name)
                primary_keys = inspector.get_pk_constraint(table_name)
                foreign_keys = [
                    {"column": fk["constrained_columns"][0], "references": fk["referred_table"]}
                    for fk in inspector.get_foreign_keys(table_name)
                ]

                schema_info["tables"].append({
                    "name": table_name,
                    "columns": [
                        {"name": col["name"], "type": str(col["type"])}
                        for col in columns
                    ],
                    "primary_keys": primary_keys,
                    "foreign_keys": foreign_keys
                })

            if db_type == "mysql":
                date_query = text("""
                    SELECT 
                        GROUP_CONCAT(
                            CONCAT('SELECT MIN(', COLUMN_NAME, ') AS min_date, MAX(', COLUMN_NAME, ') AS max_date FROM ', TABLE_NAME)
                            SEPARATOR ' UNION ALL '
                        ) AS query_string
                    FROM INFORMATION_SCHEMA.COLUMNS
                    WHERE TABLE_SCHEMA = DATABASE()
                        AND DATA_TYPE IN ('date', 'datetime', 'timestamp', 'time');
                """)

            elif db_type == "postgres":
                date_query = text("""
                    SELECT 
                        STRING_AGG(
                            'SELECT MIN(' || column_name || ') AS min_date, MAX(' || column_name || ') AS max_date FROM ' || table_name, 
                            ' UNION ALL '
                        ) AS query_string
                    FROM information_schema.columns
                    WHERE table_schema = 'public'
                        AND data_type IN ('date', 'timestamp');
                """)

            else:
                print(f"Unsupported database type: {db_type}")
                return schema_info  # Return schema info even if date logic fails

            if db_type in ["mysql", "postgres"]:
                result = connection.execute(date_query).fetchone()
                if result and result[0]:  # Ensure query_string exists
                    query_string = result[0]
                    final_result = connection.execute(text(query_string)).fetchall()

                    # Extract valid dates
                    valid_dates = [(row.min_date, row.max_date) for row in final_result 
                                    if row.min_date is not None and row.max_date is not None]

                    if valid_dates:
                        min_date = min(date[0] for date in valid_dates)
                        max_date = max(date[1] for date in valid_dates)
            elif db_type == "sqlite":
                for table in tables:
                    columns = inspector.get_columns(table)
                    date_columns = [col["name"] for col in columns if "date" in str(col["type"]).lower() or "timestamp" in str(col["type"]).lower()]
                    
                    for col in date_columns:
                        date_range_query = text(f"SELECT MIN({col}) AS min_date, MAX({col}) AS max_date FROM {table}")
                        result = connection.execute(date_range_query).fetchone()

                        if result and result.min_date and result.max_date:
                            if min_date is None or result.min_date < min_date:
                                min_date = result.min_date
                            if max_date is None or result.max_date > max_date:
                                max_date = result.max_date

        schema_info["min_date"] = min_date.isoformat() if isinstance(min_date, (datetime, date)) else None
        schema_info["max_date"] = max_date.isoformat() if isinstance(max_date, (datetime, date)) else None
        print(f"Database Date Range: Min Date: {min_date}, Max Date: {max_date}")

    except Exception as e:
        print(f"Error fetching date range: {e}. Returning schema info with default date range.")
        schema_info["min_date"] = None
        schema_info["max_date"] = None

    return schema_info

def get_external_db_session(external_db: ExternalDBModel):
    """
    Creates a dynamic session for an external database.

    :param external_db: ExternalDBModel instance containing the DB connection string.
    :return: SQLAlchemy session and engine
    """
    engine = create_engine(external_db.connection_string)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal(), engine  # Return session and engine
