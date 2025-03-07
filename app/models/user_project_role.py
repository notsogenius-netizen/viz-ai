from sqlalchemy import Column, Integer, ForeignKey, DateTime, func
from sqlalchemy.orm import relationship
from app.core.base import Base
from uuid import uuid4

class UserProjectRole(Base):
    __tablename__ = "user_project_role"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    project_id = Column(Integer, ForeignKey("projects.id"))
    role_id = Column(Integer, ForeignKey("roles.id"))
    created_at= Column(DateTime, nullable= False, server_default=func.now())

    user = relationship("UserModel", back_populates="user_project_roles")
    project = relationship("ProjectModel", back_populates="user_project_roles")
    role = relationship("RoleModel", back_populates= "user_project_roles")