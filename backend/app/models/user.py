from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from app.db.database import Base


class User(Base):
    __tablename__ = "user"

    id            = Column(Integer, primary_key=True, autoincrement=True)
    company_id    = Column(Integer, ForeignKey("company.id"), nullable=True)
    username      = Column(String(100), nullable=False, unique=True, index=True)
    name          = Column(String(255), nullable=False)
    email         = Column(String(255), nullable=False, unique=True, index=True)
    password_hash = Column(String, nullable=False)
    role          = Column(String(50), nullable=False, default="admin")
    created_at    = Column(DateTime, server_default=func.now())
    updated_at    = Column(DateTime, server_default=func.now(), onupdate=func.now())
    deleted_at    = Column(DateTime, nullable=True)

    company       = relationship("Company", foreign_keys=[company_id],
                                 back_populates="users")
    owned_company = relationship("Company", foreign_keys="Company.admin_user_id",
                                 back_populates="owner", uselist=False)