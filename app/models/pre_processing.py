from uuid import uuid4
from sqlalchemy import Column, String, ForeignKey, DateTime, func, Text, Double, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from app.core.base import Base
from app.models.post_processing import dashboard_query_association

class ExternalDBModel(Base):
    __tablename__ = 'external_db'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_project_role_id = Column(UUID, ForeignKey('user_project_role.id'), nullable=False)
    connection_string = Column(String, nullable=False)
    domain = Column(String, nullable=True)
    db_metadata = Column(Text, nullable=True)
    schema_structure = Column(Text, nullable=False)
    database_provider = Column(Text, nullable=True) 
    min_date = Column(DateTime, nullable= True)
    max_date = Column(DateTime, nullable= True)
    created_at= Column(DateTime, nullable= False, server_default=func.now())

    dashboards = relationship("Dashboard", back_populates="external_db", cascade="all, delete-orphan")

    user_project_role = relationship(
        "UserProjectRole",
        back_populates="external_db",
        foreign_keys="[UserProjectRole.external_db_id]"
    )

    queries = relationship(
        "GeneratedQuery",
        back_populates="external_db",
        cascade="all, delete-orphan"
    )

class GeneratedQuery(Base):
    __tablename__ = 'generated_queries'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    external_db_id = Column(UUID, ForeignKey('external_db.id'), nullable=False)
    user_id = Column(UUID, ForeignKey("users.id"), nullable=False)
    is_sent = Column(Boolean, nullable=False, default=False)
    query_text = Column(String, nullable=False)
    explanation = Column(String, nullable=False)
    relevance = Column(Double, nullable=False)
    is_time_based = Column(Boolean, nullable=False)
    chart_type = Column(String, nullable= False)
    created_at= Column(DateTime, nullable= False, server_default=func.now())

    dashboards = relationship("Dashboard", secondary=dashboard_query_association, back_populates="queries")
    user = relationship("UserModel", back_populates="queries") 
    external_db = relationship("ExternalDBModel", back_populates="queries")