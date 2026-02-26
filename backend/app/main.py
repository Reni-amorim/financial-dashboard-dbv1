from fastapi import FastAPI
from app.api.auth import router as auth_router
from app.db.database import Base, engine
from app.api.dashboard import router as dashboard_router
from app.db.database import Base, engine
from app.api.upload import router as upload_router

app = FastAPI(title="Financial Dashboard API")

# cria tabelas no startup (MVP)
Base.metadata.create_all(bind=engine)

@app.get("/health")
def health():
    return {"status": "ok"}

app.include_router(auth_router)
app.include_router(dashboard_router)
app.include_router(upload_router)