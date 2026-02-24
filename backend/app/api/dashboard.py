from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.database import get_db
from app.models.user import User

router = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard"])

@router.get("/")
def get_dashboard(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # MVP: retorna métricas zeradas. Depois ligamos com Parquet/DB.
    return {
        "username": current_user.username,
        "total_revenue": 0.0,
        "total_debits": 0.0,
        "net_amount": 0.0,
        "transactions": 0,
    }
