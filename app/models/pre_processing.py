from sqlalchemy import Column, String, ForeignKey, DateTime, func, Integer, JSON
from sqlalchemy.orm import relationship
from app.core.base import Base

class PreProcessingModel(Base):
    __tablename__ = 'preprocessing'

    id = Column(Integer, primary_key=True)
    user_project_role_id = Column(Integer, ForeignKey('user_project_role.id'), nullable=False)
    schema_json = Column(JSON, nullable=False)
    created_at= Column(DateTime, nullable= False, server_default=func.now())


    user_project_role = relationship("UserProjectRole", back_populates="preprocessing_records")

    queries = relationship(
        "GeneratedQuery",
        back_populates="pre_processing",
        cascade="all, delete-orphan"
    )

class GeneratedQuery(Base):
    __tablename__ = 'generated_queries'

    id = Column(Integer, primary_key=True)
    pre_processing_id = Column(Integer, ForeignKey('preprocessing.id'), nullable=False)
    query_text = Column(String, nullable=False)
    created_at= Column(DateTime, nullable= False, server_default=func.now())

    pre_processing = relationship("PreProcessing", back_populates="queries")
    