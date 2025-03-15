from sqlalchemy import create_engine, text
from sqlalchemy import inspect

def get_schema_structure(connection_string: str):
    """
    Connects to the external database and retrieves the schema structure, including primary & foreign keys.
    """
    engine = create_engine(connection_string)
    inspector = inspect(engine)

    schema_info = {"tables": []}
    min_date, max_date = None, None
    
    with engine.connect() as connection:
        for table_name in inspector.get_table_names():
            columns = inspector.get_columns(table_name)
            primary_keys = inspector.get_pk_constraint(table_name)
            foreign_keys = [
                {"column": fk["constrained_columns"][0], "references": fk["referred_table"]}
                for fk in inspector.get_foreign_keys(table_name)
            ]

            # Find Date/Time columns and get their min/max values
            date_columns = [
                r'DATE_FORMAT', r'YEAR\s*\(', r'MONTH\s*\(', r'DAY\s*\(', 
                r'QUARTER\s*\(', r'WEEK\s*\(', r'DATE_SUB', r'DATE_ADD',
                r'DATE_DIFF', r'BETWEEN.*AND', r'>\s*\d{4}-\d{2}-\d{2}',
                r'<\s*\d{4}-\d{2}-\d{2}', r'GROUP BY.*year', r'GROUP BY.*month',
                r'GROUP BY.*quarter', r'GROUP BY.*date', r'\[MIN_DATE\]', r'\[MAX_DATE\]'
            ]

            for col in date_columns:
                try:
                    query = text(f"SELECT MIN({col}) AS min_date, MAX({col}) AS max_date FROM {table_name}")
                    result = connection.execute(query).fetchone()
                    
                    if result["min_date"] and result["max_date"]:
                        if min_date is None or result["min_date"] < min_date:
                            min_date = result["min_date"]
                        if max_date is None or result["max_date"] > max_date:
                            max_date = result["max_date"]

                except Exception:
                    pass 

            schema_info["tables"].append({
                "name": table_name,
                "columns": [
                    {"name": col["name"], "type": str(col["type"])}
                    for col in columns
                ],
                "primary_keys": primary_keys,
                "foreign_keys": foreign_keys
            })
    
    print(min_date)

    # Add global date range to schema info
    schema_info["min_date"] = min_date
    schema_info["max_date"] = max_date

    return schema_info