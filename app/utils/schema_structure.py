import sqlalchemy
from sqlalchemy import inspect

def get_schema_structure(connection_string: str):
    """
    Connects to the external database and retrieves the schema structure, including primary & foreign keys.
    """
    engine = sqlalchemy.create_engine(connection_string)
    inspector = inspect(engine)

    schema_info = {"tables": []}
    
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

    return schema_info