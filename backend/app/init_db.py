"""
Inicialização do banco de dados
Cria todas as tabelas automaticamente
"""
from app.db.database import engine, Base
from app.models.user import User
from app.models.upload import Upload
import logging

logger = logging.getLogger(__name__)


def init_database():
    """
    Cria todas as tabelas no banco de dados
    Executa automaticamente ao iniciar o backend
    """
    try:
        logger.info("🔄 Verificando/criando tabelas no banco de dados...")
        
        # Cria todas as tabelas
        Base.metadata.create_all(bind=engine)
        
        logger.info("✅ Tabelas verificadas/criadas com sucesso!")
        
        # Lista tabelas criadas
        from sqlalchemy import inspect
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        logger.info(f"📋 Tabelas no banco: {', '.join(tables)}")
        
    except Exception as e:
        logger.error(f"❌ Erro ao inicializar banco de dados: {e}")
        raise


if __name__ == "__main__":
    init_database()