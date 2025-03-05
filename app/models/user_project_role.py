from sqlalchemy import Column, String, UUID, ForeignKey, DateTime, func
from sqlalchemy.orm import relationship
from app.core.db import Base
from uuid import uuid4

class UserProjectRole(Base):
    __tablename__ = "user_project_role"

    id = Column(UUID(as_uuid= True), primary_key= True, default= uuid4)
    user_id = Column(UUID(as_uuid= True), ForeignKey("users.id"))
    project_id = Column(UUID(as_uuid= True), ForeignKey("projects.id"))
    role_id = Column(UUID(as_uuid= True), ForeignKey("roles.id"))
    created_at= Column(DateTime, nullable= False, server_default=func.now())

    user = relationship("User", back_populates="project_roles")
    project = relationship("Project", back_populates="project_roles")