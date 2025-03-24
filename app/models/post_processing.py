from sqlalchemy import Column, String, ForeignKey, DateTime, func, Table
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from app.core.base import Base
from uuid import uuid4

class DashboardQueryAssociation(Base):
    __tablename__ = "dashboard_query_association"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    dashboard_id = Column(UUID, ForeignKey("dashboard.id", ondelete="CASCADE"), nullable=False)
    query_id = Column(UUID, ForeignKey("generated_queries.id", ondelete="SET NULL"), nullable=True)

    dashboard = relationship("Dashboard", back_populates="dashboard_query_links")
    query = relationship("GeneratedQuery", back_populates="dashboard_query_links")

class Dashboard(Base):
    __tablename__ = "dashboard"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(String, nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    external_db_id = Column(UUID, ForeignKey("external_db.id"), nullable=False)
    user_project_role_id = Column(UUID, ForeignKey('user_project_role.id'), nullable=False)
    
    user_project_role = relationship("UserProjectRole", back_populates="dashboards")
    external_db = relationship("ExternalDBModel", back_populates="dashboards")

    queries = relationship("GeneratedQuery", secondary="dashboard_query_association", back_populates="dashboards", overlaps="dashboard_query_links")

    dashboard_query_links = relationship("DashboardQueryAssociation", back_populates="dashboard", cascade="all, delete-orphan", overlaps="queries")