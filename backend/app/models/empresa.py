"""
Model de Empresa - Gerencia cadastro de empresas do usuário
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from app.db.database import Base


class Empresa(Base):
    """
    Modelo de empresa vinculada ao usuário.
    Um usuário pode ter múltiplas empresas.
    """
    __tablename__ = "empresas"

    id         = Column(Integer, primary_key=True, index=True)
    user_id    = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"),
                        nullable=False, index=True)

    # Dados da empresa
    nome       = Column(String(255), nullable=False)
    cnpj       = Column(String(18), nullable=False)       # "XX.XXX.XXX/XXXX-XX"
    estado     = Column(String(2), nullable=False)         # "SP", "RJ"...
    regime_tributario = Column(String(50), nullable=False)
    # Valores: "Simples Nacional", "Lucro Presumido", "Lucro Real"

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relacionamento com User
    user = relationship("User", backref="empresas")