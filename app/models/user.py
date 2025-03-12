from sqlalchemy import Column, String, ForeignKey, DateTime, func, Integer
from sqlalchemy.orm import relationship
from app.core.base import Base
from uuid import uuid4

class UserModel(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String, unique=True, nullable=False)
    password = Column(String, nullable=False)
    name = Column(String, nullable=False)
    tenant_id = Column(Integer, ForeignKey("tenants.id"))
    refresh_token = Column(String, nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    tenant = relationship("TenantModel", back_populates="users", foreign_keys=[tenant_id])
    user_project_roles = relationship("UserProjectRole", back_populates="user")

    # ✅ Super User Reference
    super_tenant = relationship("TenantModel", back_populates="super_user", foreign_keys="[TenantModel.super_user_id]")


class ProjectModel(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    tenant_id = Column(Integer, ForeignKey("tenants.id"))
    created_at= Column(DateTime, nullable= False, server_default=func.now())

    tenant = relationship("TenantModel", back_populates="projects")
    user_project_roles = relationship("UserProjectRole", back_populates="project")

class RoleModel(Base):
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, unique=True, nullable=False)

    user_project_roles = relationship("UserProjectRole", back_populates= "role")

class TenantModel(Base):
    __tablename__ = "tenants"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, unique=True, nullable=False, index=True)
    super_user_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    users = relationship("UserModel", back_populates="tenant", foreign_keys="[UserModel.tenant_id]")
    projects = relationship("ProjectModel", back_populates="tenant")

    # ✅ Super User Relationship
    super_user = relationship("UserModel", back_populates="super_tenant", foreign_keys=[super_user_id])


class UserProjectRole(Base):
    __tablename__ = "user_project_role"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    project_id = Column(Integer, ForeignKey("projects.id"))
    role_id = Column(Integer, ForeignKey("roles.id"))
    external_db_id = Column(Integer, ForeignKey("external_db.id"), nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    user = relationship("UserModel", back_populates="user_project_roles")
    project = relationship("ProjectModel", back_populates="user_project_roles")
    role = relationship("RoleModel", back_populates="user_project_roles")

    external_db = relationship(
        "ExternalDBModel",
        back_populates="user_project_role",
        foreign_keys=[external_db_id]  # ✅ Explicitly define the foreign key
    )