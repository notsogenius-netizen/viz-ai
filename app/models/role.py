from sqlalchemy import Column, String, Integer
from sqlalchemy.orm import relationship
from app.core.base import Base
from uuid import uuid4

class RoleModel(Base):
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, unique=True, nullable=False)

    user_project_roles = relationship("UserProjectRole", back_populates= "role")