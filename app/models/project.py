from sqlalchemy import Column, String, UUID, ForeignKey, DateTime, func
from sqlalchemy.orm import relationship
from app.core.db import Base
from uuid import uuid4

class Project(Base):
    __tablename__ = "projects"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(String, nullable=False)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"))
    created_at= Column(DateTime, nullable= False, server_default=func.now())

    tenant = relationship("Tenant", back_populates="projects")
    user_project_roles = relationship("UserProjectRole", back_populates="project")