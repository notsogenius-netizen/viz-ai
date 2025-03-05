from sqlalchemy import Column, String, UUID, ForeignKey, DateTime, func
from sqlalchemy.orm import relationship
from app.core.db import Base
from uuid import uuid4

class Tenant(Base):
    __tablename__ = "tenants"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(String, unique=True, nullable=False)
    super_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    created_at= Column(DateTime, nullable= False, server_default=func.now())

    users = relationship("User", back_populates="tenant")
    projects = relationship("Project", back_populates="tenant")