from sqlalchemy import Column, String, ForeignKey, DateTime, func, Integer, Text
from sqlalchemy.orm import relationship
from app.core.base import Base

class ExternalDBModel(Base):
    __tablename__ = 'external_db'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_project_role_id = Column(Integer, ForeignKey('user_project_role.id'), nullable=False)
    connection_string = Column(String, nullable=False)
    domain = Column(String, nullable=False)
    db_metadata = Column(Text, nullable=True)
    schema_structure = Column(Text, nullable=True)
    created_at= Column(DateTime, nullable= False, server_default=func.now())


    user_project_role = relationship(
        "UserProjectRole",
        back_populates="external_db",
        foreign_keys="[UserProjectRole.external_db_id]"  # ✅ Explicit foreign key mapping
    )

    queries = relationship(
        "GeneratedQuery",
        back_populates="external_db",  # ✅ This must match the related attribute in GeneratedQuery
        cascade="all, delete-orphan"
    )

class GeneratedQuery(Base):
    __tablename__ = 'generated_queries'

    id = Column(Integer, primary_key=True)
    external_db_id = Column(Integer, ForeignKey('external_db.id'), nullable=False)
    query_text = Column(String, nullable=False)
    created_at= Column(DateTime, nullable= False, server_default=func.now())

    external_db = relationship("ExternalDBModel", back_populates="queries")