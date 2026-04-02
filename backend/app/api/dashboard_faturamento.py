import os
from glob import glob
import pandas as pd
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.database import get_db
from app.models.user import User
from app.services.financial_calculator import calcular_metricas

router = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard"])


def _latest_parquet_for_user(user_id: int, upload_type: str = "faturamento") -> str | None:
    """Retorna o arquivo Parquet mais recente do usuário por tipo"""
    pattern = os.path.join("data", upload_type, str(user_id), "*.parquet")
    files   = glob(pattern)
    if not files:
        return None
    files.sort(key=os.path.getmtime, reverse=True)
    return files[0]


@router.get("/")
def get_dashboard(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retorna dados do dashboard de faturamento"""

    parquet_path = _latest_parquet_for_user(current_user.id, upload_type="faturamento")

    if not parquet_path:
        return {
            "username":     current_user.username,
            "transactions": 0,
            "metricas":     {},
            "source_file":  None,
            "message":      "Faça um upload de uma planilha de faturamento para obter o relatório",
        }

    df = pd.read_parquet(parquet_path)

    print(f"\n{'='*60}")
    print(f"📊 DASHBOARD - Carregando dados")
    print(f"{'='*60}")
    print(f"Arquivo: {os.path.basename(parquet_path)}")
    print(f"Linhas:  {len(df)}")

    metricas = calcular_metricas(df)

    print(f"   ✅ Créditos:    R$ {metricas['total_creditos']:,.2f}")
    print(f"   ❌ Débitos:     R$ {metricas['total_debitos_com_icms']:,.2f}")
    print(f"   🧾 ICMS Total:  R$ {metricas['total_icms_total']:,.2f}")
    print(f"   💵 Líquido sem Rebate: R$ {metricas['total_liquido_sem_rebate']:,.2f}")
    print(f"{'='*60}\n")

    return {
        "username":     current_user.username,
        "transactions": int(len(df)),
        "metricas":     metricas,
        "source_file":  os.path.basename(parquet_path),
    }