import os
from glob import glob
import pandas as pd
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.database import get_db
from app.models.user import User
from app.services.anuncios_calculator import calcular_metricas_anuncios

router = APIRouter(prefix="/api/v1/dashboard/anuncios", tags=["dashboard-anuncios"])


def _latest_parquet(user_id: int) -> str | None:
    pattern = os.path.join("data", "anuncios", str(user_id), "*.parquet")
    files   = glob(pattern)
    if not files:
        return None
    files.sort(key=os.path.getmtime, reverse=True)
    return files[0]


@router.get("/")
def get_dashboard_anuncios(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retorna dados do dashboard de anúncios patrocinados"""

    parquet_path = _latest_parquet(current_user.id)

    if not parquet_path:
        return {
            "username":       current_user.username,
            "total_anuncios": 0,
            "metricas":       {},
            "source_file":    None,
            "message":        "Faça upload de uma planilha de anúncios patrocinados para ver o relatório",
        }

    df = pd.read_parquet(parquet_path)

    print(f"\n{'='*60}")
    print(f"📢 DASHBOARD ANÚNCIOS - Carregando dados")
    print(f"{'='*60}")
    print(f"Arquivo: {os.path.basename(parquet_path)}")
    print(f"Linhas:  {len(df)}")

    # Delega todos os cálculos ao anuncios_calculator
    metricas = calcular_metricas_anuncios(df)

    print(f"   📢 Anúncios:    {metricas['total_anuncios']}")
    print(f"   💰 Receita:     R$ {metricas['total_receita']:,.2f}")
    print(f"   💸 Investimento: R$ {metricas['total_investimento']:,.2f}")
    print(f"   📈 ROAS global: {metricas['roas_global']:.2f}x")
    print(f"   📉 ACOS global: {metricas['acos_global']:.2f}%")
    print(f"{'='*60}\n")

    return {
        "username":       current_user.username,
        "total_anuncios": metricas["total_anuncios"],
        "metricas":       metricas,
        "source_file":    os.path.basename(parquet_path),
    }