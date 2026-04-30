from sqlalchemy import Column, Integer, String, Text, Numeric, DateTime, ForeignKey, func, text
from sqlalchemy.orm import relationship
from app.db.database import Base


class Orders(Base):
    __tablename__ = "orders"

    id                     = Column(Integer, primary_key=True, autoincrement=True)
    external_order_id      = Column(String(50), nullable=False)
    account_id             = Column(Integer, ForeignKey("account.id"), nullable=False)
    status                 = Column(Text, nullable=True)
    data_criacao           = Column(DateTime, nullable=True)
    valor                  = Column(Numeric, nullable=True)
    pago                   = Column(Numeric, nullable=True)
    receita_produtos       = Column(Numeric, nullable=True)
    acrescimo_parcelamento = Column(Numeric, nullable=True)
    tarifa_venda           = Column(Numeric, nullable=True)
    parcelas               = Column(Integer, nullable=True)
    valor_parcela          = Column(Numeric, nullable=True)
    total_refund           = Column(Numeric, nullable=True)
    rebate_meli            = Column(Numeric, nullable=True)
    receita_envio          = Column(Numeric, nullable=True)
    tarifa_envio           = Column(Numeric, nullable=True)
    custo_envio_declarado  = Column(Numeric, nullable=True, server_default=text('0'))
    custo_diferenca_peso   = Column(Numeric, nullable=True, server_default=text('0'))
    created_at             = Column(DateTime, server_default=func.now())
    updated_at             = Column(DateTime, server_default=func.now(), onupdate=func.now())
    created_by             = Column(String(100), nullable=True)
    updated_by             = Column(String(100), nullable=True)
    deleted_at             = Column(DateTime, nullable=True)

    account  = relationship("Account", back_populates="orders")
    items    = relationship("ItemsOrder", back_populates="order")
    shipping = relationship("Shipping", back_populates="order", uselist=False)
    billing  = relationship("Billing", back_populates="order", uselist=False)