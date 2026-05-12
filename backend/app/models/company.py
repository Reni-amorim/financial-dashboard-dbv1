from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from app.db.database import Base


class Company(Base):
    __tablename__ = "company"

    id             = Column(Integer, primary_key=True, autoincrement=True)
    admin_user_id  = Column(Integer, ForeignKey("user.id"), nullable=False)
    name           = Column(String(255), nullable=False)
    document       = Column(String(20), nullable=True)
    state_origin   = Column(String(2), nullable=True)
    regime_tributario = Column(String(50), nullable=True)
    created_at     = Column(DateTime, server_default=func.now())
    updated_at     = Column(DateTime, server_default=func.now(), onupdate=func.now())
    created_by     = Column(String(100), nullable=True)
    updated_by     = Column(String(100), nullable=True)
    deleted_at     = Column(DateTime, nullable=True)

    owner      = relationship("User", foreign_keys=[admin_user_id], back_populates="owned_company")
    users      = relationship("User", foreign_keys="User.company_id", back_populates="company")
    businesses = relationship("Business", back_populates="company")
    products   = relationship("Product", back_populates="company")