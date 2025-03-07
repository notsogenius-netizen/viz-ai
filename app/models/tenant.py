from sqlalchemy import Column, String, ForeignKey, DateTime, Integer, func
from sqlalchemy.orm import relationship
from app.core.base import Base
from uuid import uuid4

class TenantModel(Base):
    __tablename__ = "tenants"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, unique=True, nullable=False, index= True)
    super_user_id = Column(Integer, ForeignKey("users.id"))
    created_at= Column(DateTime, nullable= False, server_default=func.now())

    users = relationship("UserModel", back_populates="tenant", foreign_keys="[UserModel.tenant_id]")
    projects = relationship("ProjectModel", back_populates="tenant")