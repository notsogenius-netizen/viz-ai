from sqlalchemy import Column, String, UUID
from sqlalchemy.orm import relationship
from app.core.base import Base
from uuid import uuid4

class RoleModel(Base):
    __tablename__ = "roles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(String, unique=True, nullable=False)

    user_project_roles = relationship("UserProjectRole", back_populates= "role")