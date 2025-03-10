from sqlalchemy import Column, String, Integer, UUID, ForeignKey, DateTime, func
from sqlalchemy.orm import relationship
from app.core.base import Base
from uuid import uuid4

class ProjectModel(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    tenant_id = Column(Integer, ForeignKey("tenants.id"))
    created_at= Column(DateTime, nullable= False, server_default=func.now())

    tenant = relationship("TenantModel", back_populates="projects")
    user_project_roles = relationship("UserProjectRole", back_populates="project")