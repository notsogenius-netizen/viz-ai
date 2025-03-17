from sqlalchemy import Column, String, ForeignKey, DateTime, func, Integer, Table
from sqlalchemy.orm import relationship
from app.core.base import Base

dashboard_query_association = Table(
    "dashboard_query_association",
    Base.metadata,
    Column("dashboard_id", Integer, ForeignKey("dashboard.id"), primary_key=True),
    Column("query_id", Integer, ForeignKey("generated_queries.id"), primary_key=True)
)

class Dashboard(Base):
    __tablename__ = "dashboard"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)

    external_db_id = Column(Integer, ForeignKey("external_db.id"), nullable=False)

    external_db = relationship("ExternalDBModel", back_populates="dashboards")
    queries = relationship("GeneratedQuery", secondary= dashboard_query_association, back_populates="dashboards")