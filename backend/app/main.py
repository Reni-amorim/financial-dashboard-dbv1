"""
Financial Dashboard API - Main
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

from app.api import upload, auth
from app.api import dashboard_faturamento
from app.api import dashboard_anuncios
from app.api import dashboard_analitico
from app.api import company
from app.api import business
from app.api import account

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Financial Dashboard API",
    version="1.0.0",
    description="API para upload e análise de planilhas financeiras"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8501", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(upload.router)
app.include_router(dashboard_faturamento.router)
app.include_router(dashboard_anuncios.router)
app.include_router(dashboard_analitico.router)
app.include_router(company.router)
app.include_router(business.router)
app.include_router(account.router)

@app.get("/")
def root():
    return {"message": "Financial Dashboard API", "version": "1.0.0", "status": "running"}


@app.get("/health")
def health():
    return {"status": "healthy"}

@app.get("/health/external-db")
def health_external_db():
    from app.db.external_database import test_external_connection
    from fastapi import HTTPException
    try:
        test_external_connection()
        return {"status": "healthy", "db": "meli"}
    except Exception as e:
        logger.error(f"External DB check falhou: {e}")
        raise HTTPException(status_code=503, detail=f"External DB indisponível: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

##### Somente para commitar a alteração feita anteriormente #####