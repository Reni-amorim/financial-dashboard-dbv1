"""
Endpoint do Dashboard de Anúncios Patrocinados
GET /api/v1/dashboard/anuncios
"""
import os
from glob import glob
import pandas as pd
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.database import get_db
from app.models.user import User

router = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard"])


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def _latest_parquet(user_id: int, upload_type: str) -> str | None:
    pattern = os.path.join("data", upload_type, str(user_id), "*.parquet")
    files = glob(pattern)
    if not files:
        return None
    files.sort(key=os.path.getmtime, reverse=True)
    return files[0]


def _safe_float(val) -> float:
    try:
        f = float(val)
        return 0.0 if (f != f) else f  # NaN check
    except Exception:
        return 0.0


def _safe_int(val) -> int:
    try:
        return int(val)
    except Exception:
        return 0


# ─────────────────────────────────────────────
# Endpoint
# ─────────────────────────────────────────────

@router.get("/anuncios")
def get_dashboard_anuncios(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Retorna dados completos do dashboard de anúncios patrocinados.

    Estrutura de retorno:
    - summary:    métricas globais (receita, investimento, ROAS, ACOS, etc.)
    - por_status: contagem e receita agrupados por status do anúncio
    - por_campanha: métricas agrupadas por campanha
    - top_anuncios: top 10 por receita (com dados completos)
    - piores_acos:  top 10 com pior ACOS (apenas anúncios com cliques)
    - source_file:  nome do arquivo Parquet utilizado
    """
    parquet_path = _latest_parquet(current_user.id, upload_type="anuncios")

    if not parquet_path:
        return {
            "username": current_user.username,
            "summary": None,
            "por_status": [],
            "por_campanha": [],
            "top_anuncios": [],
            "piores_acos": [],
            "source_file": None,
            "message": "Faça upload de uma planilha de anúncios para visualizar o dashboard.",
        }

    df = pd.read_parquet(parquet_path)

    print(f"\n{'='*60}")
    print(f"📢 DASHBOARD ANÚNCIOS — carregando dados")
    print(f"{'='*60}")
    print(f"Arquivo: {os.path.basename(parquet_path)}")
    print(f"Linhas:  {len(df)}")

    # ── Colunas esperadas (com fallback para 0) ────────────
    def col(name):
        return df[name] if name in df.columns else pd.Series([0] * len(df))

    # ── Summary global ─────────────────────────────────────
    total_receita      = _safe_float(col("Receita (Moeda local)").sum())
    total_investimento = _safe_float(col("Investimento (Moeda local)").sum())
    total_receita_dir  = _safe_float(col("Receita por vendas diretas (Moeda Local)").sum())
    total_receita_ind  = _safe_float(col("Receita por vendas indiretas").sum())
    total_impressoes   = _safe_int(col("Impressões").sum())
    total_cliques      = _safe_int(col("Cliques").sum())
    total_vendas       = _safe_int(col("Vendas por publicidade (Diretas + Indiretas)").sum())
    total_vendas_dir   = _safe_int(col("Vendas diretas").sum())
    total_vendas_ind   = _safe_int(col("Vendas indiretas").sum())

    roas_global = round(total_receita / total_investimento, 2) if total_investimento > 0 else 0.0
    acos_global = round((total_investimento / total_receita) * 100, 2) if total_receita > 0 else 0.0
    ctr_global  = round((total_cliques / total_impressoes) * 100, 4) if total_impressoes > 0 else 0.0
    cvr_global  = round((total_vendas / total_cliques) * 100, 4) if total_cliques > 0 else 0.0
    cpc_global  = round(total_investimento / total_cliques, 4) if total_cliques > 0 else 0.0

    # Status breakdown
    status_counts = {}
    if "Status" in df.columns:
        status_counts = df["Status"].value_counts().to_dict()

    summary = {
        # Anúncios
        "total_anuncios":        int(len(df)),
        "anuncios_ativos":       _safe_int(status_counts.get("Ativo", 0)),
        "anuncios_desativados":  _safe_int(status_counts.get("Desativada", 0)),
        "anuncios_movidos":      _safe_int(status_counts.get("Movido", 0)),
        "anuncios_sem_status":   _safe_int(status_counts.get("Sem status", 0)),
        # Volume
        "total_impressoes":      total_impressoes,
        "total_cliques":         total_cliques,
        "total_vendas":          total_vendas,
        "total_vendas_diretas":  total_vendas_dir,
        "total_vendas_indiretas": total_vendas_ind,
        # Financeiro
        "total_receita":          total_receita,
        "total_investimento":     total_investimento,
        "total_receita_direta":   total_receita_dir,
        "total_receita_indireta": total_receita_ind,
        # Eficiência global
        "roas_global": roas_global,
        "acos_global": acos_global,
        "ctr_global":  ctr_global,
        "cvr_global":  cvr_global,
        "cpc_global":  cpc_global,
    }

    print(f"💰 Receita:      R$ {total_receita:,.2f}")
    print(f"📈 ROAS global:  {roas_global:.2f}x")
    print(f"📉 ACOS global:  {acos_global:.2f}%")

    # ── Por status ─────────────────────────────────────────
    por_status = []
    if "Status" in df.columns:
        grp = df.groupby("Status", dropna=False).agg(
            quantidade=("Status", "count"),
            receita=("Receita (Moeda local)", "sum"),
            investimento=("Investimento (Moeda local)", "sum"),
            cliques=("Cliques", "sum"),
            impressoes=("Impressões", "sum"),
            vendas=("Vendas por publicidade (Diretas + Indiretas)", "sum"),
        ).reset_index()

        for _, row in grp.iterrows():
            rec = _safe_float(row["receita"])
            inv = _safe_float(row["investimento"])
            por_status.append({
                "status":       str(row["Status"]),
                "quantidade":   _safe_int(row["quantidade"]),
                "receita":      rec,
                "investimento": inv,
                "cliques":      _safe_int(row["cliques"]),
                "impressoes":   _safe_int(row["impressoes"]),
                "vendas":       _safe_int(row["vendas"]),
                "roas":         round(rec / inv, 2) if inv > 0 else 0.0,
                "acos":         round((inv / rec) * 100, 2) if rec > 0 else 0.0,
            })

    # ── Por campanha ───────────────────────────────────────
    por_campanha = []
    if "Campanha" in df.columns:
        grp = df.groupby("Campanha", dropna=False).agg(
            total_anuncios=("Campanha", "count"),
            impressoes=("Impressões", "sum"),
            cliques=("Cliques", "sum"),
            receita=("Receita (Moeda local)", "sum"),
            investimento=("Investimento (Moeda local)", "sum"),
            vendas=("Vendas por publicidade (Diretas + Indiretas)", "sum"),
            vendas_diretas=("Vendas diretas", "sum"),
            vendas_indiretas=("Vendas indiretas", "sum"),
            receita_direta=("Receita por vendas diretas (Moeda Local)", "sum"),
            receita_indireta=("Receita por vendas indiretas", "sum"),
        ).reset_index()

        for _, row in grp.iterrows():
            rec  = _safe_float(row["receita"])
            inv  = _safe_float(row["investimento"])
            imp  = _safe_int(row["impressoes"])
            cli  = _safe_int(row["cliques"])
            vnd  = _safe_int(row["vendas"])
            por_campanha.append({
                "campanha":         str(row["Campanha"]),
                "total_anuncios":   _safe_int(row["total_anuncios"]),
                "impressoes":       imp,
                "cliques":          cli,
                "receita":          rec,
                "investimento":     inv,
                "vendas":           vnd,
                "vendas_diretas":   _safe_int(row["vendas_diretas"]),
                "vendas_indiretas": _safe_int(row["vendas_indiretas"]),
                "receita_direta":   _safe_float(row["receita_direta"]),
                "receita_indireta": _safe_float(row["receita_indireta"]),
                "roas":   round(rec / inv, 2) if inv > 0 else 0.0,
                "acos":   round((inv / rec) * 100, 2) if rec > 0 else 0.0,
                "ctr":    round((cli / imp) * 100, 4) if imp > 0 else 0.0,
                "cvr":    round((vnd / cli) * 100, 4) if cli > 0 else 0.0,
                "cpc":    round(inv / cli, 4) if cli > 0 else 0.0,
            })

        por_campanha.sort(key=lambda x: x["receita"], reverse=True)

    # ── Top 10 anúncios por receita ────────────────────────
    top_anuncios = []
    df_com_receita = df[col("Receita (Moeda local)") > 0].copy() if "Receita (Moeda local)" in df.columns else df.copy()
    top_df = df_com_receita.nlargest(10, "Receita (Moeda local)") if "Receita (Moeda local)" in df_com_receita.columns else df_com_receita.head(10)

    for _, row in top_df.iterrows():
        rec = _safe_float(row.get("Receita (Moeda local)", 0))
        inv = _safe_float(row.get("Investimento (Moeda local)", 0))
        cli = _safe_int(row.get("Cliques", 0))
        imp = _safe_int(row.get("Impressões", 0))
        vnd = _safe_int(row.get("Vendas por publicidade (Diretas + Indiretas)", 0))
        top_anuncios.append({
            "titulo":          str(row.get("Título do anúncio patrocinado", "")),
            "codigo":          str(row.get("Código do anúncio", "")),
            "campanha":        str(row.get("Campanha", "")),
            "status":          str(row.get("Status", "")),
            "impressoes":      imp,
            "cliques":         cli,
            "receita":         rec,
            "investimento":    inv,
            "vendas_diretas":  _safe_int(row.get("Vendas diretas", 0)),
            "vendas_indiretas":_safe_int(row.get("Vendas indiretas", 0)),
            "vendas":          vnd,
            "receita_direta":  _safe_float(row.get("Receita por vendas diretas (Moeda Local)", 0)),
            "receita_indireta":_safe_float(row.get("Receita por vendas indiretas", 0)),
            "roas":   round(rec / inv, 2) if inv > 0 else 0.0,
            "acos":   round((inv / rec) * 100, 2) if rec > 0 else 0.0,
            "ctr":    round((cli / imp) * 100, 4) if imp > 0 else 0.0,
            "cvr":    _safe_float(row.get("CVR (Conversion rate)", 0)),
            "cpc":    _safe_float(row.get("CPC  (Custo por clique)", 0)),
        })

    # ── Top 10 piores ACOS (anúncios com cliques > 0) ─────
    piores_acos = []
    if "ACOS  (Investimento / Receitas)" in df.columns and "Cliques" in df.columns:
        df_ativos = df[(df["Cliques"] > 0) & (df["ACOS  (Investimento / Receitas)"] > 0)].copy()
        worst_df = df_ativos.nlargest(10, "ACOS  (Investimento / Receitas)")

        for _, row in worst_df.iterrows():
            rec = _safe_float(row.get("Receita (Moeda local)", 0))
            inv = _safe_float(row.get("Investimento (Moeda local)", 0))
            piores_acos.append({
                "titulo":       str(row.get("Título do anúncio patrocinado", "")),
                "codigo":       str(row.get("Código do anúncio", "")),
                "campanha":     str(row.get("Campanha", "")),
                "status":       str(row.get("Status", "")),
                "acos":         _safe_float(row.get("ACOS  (Investimento / Receitas)", 0)),
                "roas":         _safe_float(row.get("ROAS (Receitas / Investimento)", 0)),
                "receita":      rec,
                "investimento": inv,
                "cliques":      _safe_int(row.get("Cliques", 0)),
                "vendas":       _safe_int(row.get("Vendas por publicidade (Diretas + Indiretas)", 0)),
            })

    print(f"✅ Dashboard montado — {len(top_anuncios)} top anúncios, {len(por_campanha)} campanhas")
    print(f"{'='*60}\n")

    return {
        "username":     current_user.username,
        "summary":      summary,
        "por_status":   por_status,
        "por_campanha": por_campanha,
        "top_anuncios": top_anuncios,
        "piores_acos":  piores_acos,
        "source_file":  os.path.basename(parquet_path),
    }