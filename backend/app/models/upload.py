from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, func
from sqlalchemy.orm import relationship
from app.db.database import Base


class Upload(Base):
    __tablename__ = "uploads"

    id                = Column(Integer, primary_key=True, autoincrement=True)
    user_id           = Column(Integer, ForeignKey("user.id", ondelete="CASCADE"),
                               nullable=False, index=True)
    upload_type       = Column(String(50), nullable=False, default="faturamento", index=True)
    filename          = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    file_path         = Column(String(500), nullable=False)
    parquet_path      = Column(String(500), nullable=True)
    processing_status = Column(String(50), nullable=False, default="pending")
    rows_processed    = Column(Integer, nullable=True)
    error_message     = Column(Text, nullable=True)
    metrics_json      = Column(Text, nullable=True)
    uploaded_at       = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    processed_at      = Column(DateTime(timezone=True), nullable=True)

    user = relationship("User", backref="uploads")