"""
Financial Dashboard API - Main
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

from app.init_db import init_database
from app.api import upload, dashboard, auth

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Cria app
app = FastAPI(
    title="Financial Dashboard API",
    version="1.0.0",
    description="API para upload e análise de planilhas financeiras"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8501", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    """Executado ao iniciar a aplicação"""
    logger.info("🚀 Iniciando aplicação...")
    
    # Cria tabelas automaticamente
    init_database()
    
    logger.info("✅ Aplicação iniciada com sucesso!")


@app.on_event("shutdown")
async def shutdown_event():
    """Executado ao desligar"""
    logger.info("👋 Encerrando aplicação...")


# Rotas
app.include_router(auth.router)
app.include_router(upload.router)
app.include_router(dashboard.router)


@app.get("/")
def root():
    return {
        "message": "Financial Dashboard API",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health")
def health():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)