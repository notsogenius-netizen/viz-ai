from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from typing import Generator
from core.settings import settings

engine = create_engine(
    settings.DB_URI,
    pool_pre_ping= True,
    pool_recycle= 300,
    pool_size= 5,
    max_overflow=0
)

SessionLocal = sessionmaker(bind= engine, autocommit = False, autoflush= False)
Base = declarative_base()

def get_db() -> Generator:
    """Create the database tables"""
    db = SessionLocal()
    Base.metadata.create_all(engine)
    try:
        yield db
    finally:
        db.close()