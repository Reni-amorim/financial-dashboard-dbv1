from sqlalchemy import BigInteger, Column, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.db.database import Base


class Shipping(Base):
    __tablename__ = "shipping"

    id            = Column(BigInteger, primary_key=True, autoincrement=False)
    order_id      = Column(BigInteger, ForeignKey("orders.id"), nullable=True)
    receiver_name = Column(Text, nullable=True)
    cep           = Column(Text, nullable=True)
    logradouro    = Column(Text, nullable=True)
    numero        = Column(Text, nullable=True)
    complemento   = Column(Text, nullable=True)
    bairro        = Column(Text, nullable=True)
    cidade        = Column(Text, nullable=True)
    estado        = Column(Text, nullable=True)

    order = relationship("Orders", back_populates="shipping")