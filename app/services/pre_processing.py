import json
from fastapi import HTTPException
from sqlalchemy.orm import Session
from app.models.pre_processing import ExternalDBModel
from app.models.user import UserProjectRole
from app.utils.schema_structure import get_schema_structure
from app.utils.auth_dependencies import get_current_user
from app.schemas import ExternalDBCreateRequest, ExternalDBResponse, CurrentUser

async def create_or_update_external_db(data: ExternalDBCreateRequest, db: Session, current_user: CurrentUser):
    """
    Connects to the external database, retrieves schema, and saves it in the internal database.
    """
    print(current_user)
    user_id = current_user.user_id
    user_role = current_user.role

    # Check if UserProjectRole exists
    user_project_role = db.query(UserProjectRole).filter(
        UserProjectRole.user_id == user_id,
        UserProjectRole.project_id == data.project_id
    ).first()
    if not user_project_role:
        raise HTTPException(status_code=400, detail="User does not have a role in this project.")
    print(user_project_role.id)
    # Retrieve schema structure
    schema_structure = get_schema_structure(data.connection_string)
    
    # Check if entry exists (Update case)
    db_entry = db.query(ExternalDBModel).filter_by(user_project_role_id=user_project_role.id).first()
    if db_entry:
        db_entry.connection_string = data.connection_string
        db_entry.domain = data.domain
        db_entry.schema_structure = json.dumps(schema_structure)
    else:
        db_entry = ExternalDBModel(
            user_project_role_id=user_project_role.id,
            connection_string=data.connection_string,
            domain=data.domain,
            schema_structure=json.dumps(schema_structure),
        )
        db.add(db_entry)

    db.commit()
    db.refresh(db_entry)

    return ExternalDBResponse(
        id=db_entry.id,
        user_project_role_id=db_entry.user_project_role_id,
        connection_string=db_entry.connection_string,
        domain=db_entry.domain,
        schema_structure=schema_structure,
    )