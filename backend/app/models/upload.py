"""
Model de Upload - Gerencia uploads de planilhas
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, func
from sqlalchemy.orm import relationship
from app.db.database import Base


class Upload(Base):
    """
    Modelo de upload de arquivos
    
    Suporta múltiplos tipos: faturamento, anuncios, etc.
    """
    __tablename__ = "uploads"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Tipo de upload
    upload_type = Column(String(50), default="faturamento", nullable=False, index=True)
    # Valores possíveis: "faturamento", "anuncios"
    
    # Informações do arquivo
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    parquet_path = Column(String(500), nullable=True)
    
    # Status do processamento
    processing_status = Column(String(50), default="pending", nullable=False)
    # Valores possíveis: "pending", "processing", "completed", "failed"
    
    rows_processed = Column(Integer, nullable=True)
    error_message = Column(Text, nullable=True)
    
    # Métricas (JSON)
    metrics_json = Column(Text, nullable=True)
    
    # Timestamps
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    processed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relacionamento com User
    user = relationship("User", backref="uploads")