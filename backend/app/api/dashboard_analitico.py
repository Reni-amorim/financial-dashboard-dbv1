"""
Dashboard Analítico — cruza faturamento com anúncios patrocinados
Endpoint: GET /api/v1/dashboard/analitico
          GET /api/v1/dashboard/analitico/exportar
"""
import os
import io
import base64
from glob import glob
from datetime import date

import pandas as pd
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.database import get_db
from app.models.user import User
from app.services.analitico_calculator import calcular_analitico

router = APIRouter(prefix="/api/v1/dashboard/analitico", tags=["dashboard-analitico"])


# ─────────────────────────────────────────────────────────────
# HELPER
# ─────────────────────────────────────────────────────────────

def _latest_parquet(user_id: int, tipo: str) -> str | None:
    pattern = os.path.join("data", tipo, str(user_id), "*.parquet")
    files   = glob(pattern)
    if not files:
        return None
    files.sort(key=os.path.getmtime, reverse=True)
    return files[0]


# ─────────────────────────────────────────────────────────────
# ENDPOINTS
# ─────────────────────────────────────────────────────────────

@router.get("/")
def get_dashboard_analitico(
    page:      int = 1,
    page_size: int = 100,
    mlb:       str = "",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retorna análise cruzada faturamento × anúncios patrocinados"""

    parquet_fat  = _latest_parquet(current_user.id, "faturamento")
    parquet_anun = _latest_parquet(current_user.id, "anuncios")

    if not parquet_fat and not parquet_anun:
        return {"message": "Faça upload da planilha de faturamento e de anúncios para ver a análise cruzada.",
                "summary": {}, "acumulado": [], "vendas": []}

    if not parquet_fat:
        return {"message": "Faça upload da planilha de faturamento para cruzar com os anúncios.",
                "summary": {}, "acumulado": [], "vendas": []}

    if not parquet_anun:
        return {"message": "Faça upload da planilha de anúncios patrocinados para cruzar com o faturamento.",
                "summary": {}, "acumulado": [], "vendas": []}

    df_fat  = pd.read_parquet(parquet_fat)
    df_anun = pd.read_parquet(parquet_anun)

    print(f"\n{'='*60}")
    print(f"🔬 DASHBOARD ANALÍTICO")
    print(f"   Faturamento: {len(df_fat)} linhas")
    print(f"   Anúncios:    {len(df_anun)} linhas")
    print(f"{'='*60}")

    # Delega todos os cálculos ao analitico_calculator
    result = calcular_analitico(df_fat, df_anun, page=page, page_size=page_size, filtro_mlb=mlb)

    s = result["summary"]
    print(f"   ✅ Créditos:      R$ {s['total_creditos']:,.2f}")
    print(f"   ❌ Débitos:       R$ {s['total_debitos']:,.2f}")
    print(f"   🧾 ICMS:          R$ {s['total_icms']:,.2f}")
    print(f"   💵 Líquido sem Rebate: R$ {s['total_liquido_sem_rebate']:,.2f}")
    print(f"   📢 Anúncios:      R$ {s['total_anuncios']:,.2f}")
    print(f"   🏆 Líquido Real:  R$ {s['liquido_real']:,.2f}")
    print(f"   📊 Margem Real:   {s['margem_real']:.1f}%")
    print(f"{'='*60}\n")

    return {"username": current_user.username, **result}


@router.get("/exportar")
def exportar_analitico(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Gera planilha XLSX com o relatório analítico e retorna em base64"""

    parquet_fat  = _latest_parquet(current_user.id, "faturamento")
    parquet_anun = _latest_parquet(current_user.id, "anuncios")

    if not parquet_fat or not parquet_anun:
        return {"erro": "É necessário ter faturamento e anúncios enviados para exportar."}

    df_fat  = pd.read_parquet(parquet_fat)
    df_anun = pd.read_parquet(parquet_anun)

    # Busca todos os dados sem paginação
    result    = calcular_analitico(df_fat, df_anun, page=1, page_size=999999)
    summary   = result["summary"]
    acumulado = result["acumulado"]
    vendas    = result["vendas"]

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:

        # Aba 1: Resumo
        df_resumo = pd.DataFrame([{"Métrica": k, "Valor": v} for k, v in summary.items()])
        df_resumo.to_excel(writer, sheet_name="Resumo", index=False)

        # Aba 2: Investimento por MLB
        if acumulado:
            df_ac = pd.DataFrame(acumulado)
            df_ac.columns = ["Código MLB", "Título", "Investimento Total (R$)", "Vendas Diretas", "Custo por Venda (R$)"]
            df_ac.to_excel(writer, sheet_name="Anúncios por MLB", index=False)

        # Aba 3: Vendas detalhadas
        if vendas:
            df_v = pd.DataFrame(vendas)
            df_v.to_excel(writer, sheet_name="Vendas Detalhadas", index=False)

    output.seek(0)
    xlsx_b64 = base64.b64encode(output.read()).decode("utf-8")
    today    = date.today().strftime("%Y%m%d")

    return {"filename": f"relatorio_analitico_{today}.xlsx", "data": xlsx_b64}