from sqlalchemy import Column, Integer, String, Numeric, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from app.db.database import Base


class Product(Base):
    __tablename__ = "product"

    id         = Column(Integer, primary_key=True, autoincrement=True)
    company_id = Column(Integer, ForeignKey("company.id"), nullable=False)
    sku        = Column(String(100), nullable=False)
    name       = Column(String(255), nullable=False)
    ncm        = Column(String(20), nullable=True)
    cost_price = Column(Numeric, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    company = relationship("Company", back_populates="products")