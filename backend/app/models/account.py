from sqlalchemy import Column, Integer, BigInteger, String, Text, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from app.db.database import Base


class Account(Base):
    __tablename__ = "account"

    id             = Column(Integer, primary_key=True, autoincrement=True)
    business_id    = Column(Integer, ForeignKey("business.id"), nullable=True)
    marketplace_id = Column(BigInteger, nullable=True)
    name           = Column(String(255), nullable=True)
    access_token   = Column(Text, nullable=True)
    refresh_token  = Column(Text, nullable=True)
    status         = Column(String, nullable=True, default="active")
    created_at     = Column(DateTime, server_default=func.now())
    updated_at     = Column(DateTime, server_default=func.now(), onupdate=func.now())
    created_by     = Column(String(100), nullable=True)
    updated_by     = Column(String(100), nullable=True)
    deleted_at     = Column(DateTime, nullable=True)

    business  = relationship("Business", back_populates="accounts")
    addresses = relationship("AccountAddress", back_populates="account")
    orders    = relationship("Orders", back_populates="account")