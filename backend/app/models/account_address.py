from sqlalchemy import CHAR, Column, Integer, Text, Boolean, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from app.db.database import Base


class AccountAddress(Base):
    __tablename__ = "account_address"

    id          = Column(Integer, primary_key=True, autoincrement=True)
    account_id  = Column(Integer, ForeignKey("account.id"), nullable=False)
    tipo        = Column(Text, nullable=True)
    logradouro  = Column(Text, nullable=False)
    numero      = Column(Text, nullable=False)
    complemento = Column(Text, nullable=True)
    bairro      = Column(Text, nullable=True)
    cidade      = Column(Text, nullable=False)
    estado      = Column(CHAR(2), nullable=False)
    cep         = Column(Text, nullable=True)
    principal   = Column(Boolean, nullable=True, default=False)
    created_at  = Column(DateTime(timezone=True), server_default=func.now())

    account = relationship("Account", back_populates="addresses")