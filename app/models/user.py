from sqlalchemy import Column, String, ForeignKey, DateTime, func, Integer
from sqlalchemy.orm import relationship
from app.core.base import Base
from uuid import uuid4

class UserModel(Base):
    __tablename__="users"
    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String, unique= True, nullable= False)
    password = Column(String, nullable= False)
    name = Column(String, nullable= False)
    tenant_id = Column(Integer, ForeignKey("tenants.id"))
    refresh_token = Column(String)
    created_at= Column(DateTime, nullable= False, server_default=func.now())

    tenant = relationship("TenantModel", back_populates="users", foreign_keys=[tenant_id])
    user_project_roles = relationship("UserProjectRole", back_populates="user")