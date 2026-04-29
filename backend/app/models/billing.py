from sqlalchemy import BigInteger, Column, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.db.database import Base


class Billing(Base):
    __tablename__ = "billing"

    id           = Column(BigInteger, primary_key=True, autoincrement=True)
    order_id     = Column(BigInteger, ForeignKey("orders.id"), nullable=True)
    doc_tipo     = Column(Text, nullable=True)
    doc_numero   = Column(Text, nullable=True)
    razao_social = Column(Text, nullable=True)
    ie           = Column(Text, nullable=True)
    cep          = Column(Text, nullable=True)
    logradouro   = Column(Text, nullable=True)
    numero       = Column(Text, nullable=True)
    complemento  = Column(Text, nullable=True)
    bairro       = Column(Text, nullable=True)
    cidade       = Column(Text, nullable=True)
    estado       = Column(Text, nullable=True)

    order = relationship("Orders", back_populates="billing")