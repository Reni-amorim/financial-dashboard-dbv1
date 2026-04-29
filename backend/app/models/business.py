from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from app.db.database import Base


class Business(Base):
    __tablename__ = "business"

    id         = Column(Integer, primary_key=True, autoincrement=True)
    company_id = Column(Integer, ForeignKey("company.id"), nullable=False)
    name       = Column(String(255), nullable=False)
    document   = Column(String(20), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    created_by = Column(String(100), nullable=True)
    updated_by = Column(String(100), nullable=True)
    deleted_at = Column(DateTime, nullable=True)

    company  = relationship("Company", back_populates="businesses")
    accounts = relationship("Account", back_populates="business")