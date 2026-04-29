from sqlalchemy import Column, Integer, String, Text, Numeric, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from app.db.database import Base


class ItemsOrder(Base):
    __tablename__ = "items_order"

    id             = Column(Integer, primary_key=True, autoincrement=True)
    order_id       = Column(Integer, ForeignKey("orders.id"), nullable=False)
    sku            = Column(Text, nullable=True)
    titulo         = Column(String(255), nullable=False)
    quantidade     = Column(Integer, nullable=False)
    preco_unitario = Column(Numeric, nullable=False)
    created_at     = Column(DateTime, server_default=func.now())
    updated_at     = Column(DateTime, server_default=func.now(), onupdate=func.now())
    created_by     = Column(String(100), nullable=True)
    updated_by     = Column(String(100), nullable=True)
    deleted_at     = Column(DateTime, nullable=True)

    order = relationship("Orders", back_populates="items")