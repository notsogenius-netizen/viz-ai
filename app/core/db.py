from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from typing import Generator
from app.core.settings import settings
from app.core.base import Base
from app.models.tenant import TenantModel
from app.models.user import UserModel
from app.models.project import ProjectModel
from app.models.role import RoleModel 
from app.models.user_project_role import UserProjectRole

print(settings.DB_URI)

engine = create_engine(
    url= settings.DB_URI,
    pool_pre_ping= True,
    pool_recycle= 300,
    pool_size= 5,
    max_overflow=0
)

SessionLocal = sessionmaker(bind= engine, autoflush= False)

def get_db() -> Generator:
    """Create the database tables"""
    db = SessionLocal()
    Base.metadata.create_all(engine)
    try:
        yield db
    finally:
        db.close()