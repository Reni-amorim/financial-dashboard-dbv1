import os
import json
from glob import glob
import pandas as pd
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.database import get_db
from app.models.user import User

router = APIRouter(prefix="/api/v1/dashboard/anuncios", tags=["dashboard-anuncios"])


def _latest_parquet(user_id: int) -> str | None:
    pattern = os.path.join("data", "anuncios", str(user_id), "*.parquet")
    files = glob(pattern)
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
            "username": current_user.username,
            "total_anuncios": 0,
            "metrics": {},
            "por_campanha": [],
            "top_anuncios": [],
            "source_file": None,
            "message": "Faça upload de uma planilha de anúncios patrocinados para ver o relatório",
        }

    df = pd.read_parquet(parquet_path)

    print(f"\n{'='*60}")
    print(f"📢 DASHBOARD ANÚNCIOS - Carregando dados")
    print(f"{'='*60}")
    print(f"Arquivo: {os.path.basename(parquet_path)}")
    print(f"Linhas: {len(df)}")

    # ── Métricas globais ──────────────────────────────────
    def safe_sum(col):
        return float(df[col].sum()) if col in df.columns else 0.0

    def safe_int(col):
        return int(df[col].sum()) if col in df.columns else 0

    total_impressoes   = safe_int("Impressões")
    total_cliques      = safe_int("Cliques")
    total_vendas       = safe_int("Vendas por publicidade (Diretas + Indiretas)")
    total_vendas_dir   = safe_int("Vendas diretas")
    total_vendas_ind   = safe_int("Vendas indiretas")
    total_receita      = safe_sum("Receita (Moeda local)")
    total_investimento = safe_sum("Investimento (Moeda local)")
    total_receita_dir  = safe_sum("Receita por vendas diretas (Moeda Local)")
    total_receita_ind  = safe_sum("Receita por vendas indiretas")

    roas_global = round(total_receita / total_investimento, 2) if total_investimento > 0 else 0.0
    acos_global = round((total_investimento / total_receita) * 100, 2) if total_receita > 0 else 0.0

    df_com_cliques = df[df["Cliques"] > 0] if "Cliques" in df.columns else df
    ctr_medio = float(df_com_cliques["CTR (Click Through Rate)"].mean()) if "CTR (Click Through Rate)" in df_com_cliques.columns and len(df_com_cliques) > 0 else 0.0
    cpc_medio = float(df_com_cliques["CPC (Custo por clique)"].mean()) if "CPC (Custo por clique)" in df_com_cliques.columns and len(df_com_cliques) > 0 else 0.0
    cvr_medio = float(df_com_cliques["CVR (Conversion rate)"].mean()) if "CVR (Conversion rate)" in df_com_cliques.columns and len(df_com_cliques) > 0 else 0.0

    # Contagem por status
    status_counts = {}
    if "Status" in df.columns:
        status_counts = df["Status"].value_counts().to_dict()
        status_counts = {k: int(v) for k, v in status_counts.items()}

    metrics = {
        "total_anuncios":       int(len(df)),
        "status_counts":        status_counts,
        "total_impressoes":     total_impressoes,
        "total_cliques":        total_cliques,
        "total_vendas":         total_vendas,
        "total_vendas_diretas": total_vendas_dir,
        "total_vendas_indiretas": total_vendas_ind,
        "total_receita":        total_receita,
        "total_investimento":   total_investimento,
        "total_receita_direta": total_receita_dir,
        "total_receita_indireta": total_receita_ind,
        "roas_global":          roas_global,
        "acos_global":          acos_global,
        "ctr_medio":            round(ctr_medio, 4),
        "cpc_medio":            round(cpc_medio, 4),
        "cvr_medio":            round(cvr_medio, 4),
    }

    # ── Agrupado por campanha ─────────────────────────────
    por_campanha = []
    if "Campanha" in df.columns:
        agg = {
            col: "sum"
            for col in [
                "Impressões", "Cliques", "Vendas diretas", "Vendas indiretas",
                "Vendas por publicidade (Diretas + Indiretas)",
                "Receita (Moeda local)", "Investimento (Moeda local)",
            ]
            if col in df.columns
        }
        if agg:
            g = df.groupby("Campanha").agg(agg).reset_index()
            for _, row in g.iterrows():
                rec = row.get("Receita (Moeda local)", 0)
                inv = row.get("Investimento (Moeda local)", 0)
                por_campanha.append({
                    "campanha":     row["Campanha"],
                    "impressoes":   int(row.get("Impressões", 0)),
                    "cliques":      int(row.get("Cliques", 0)),
                    "vendas":       int(row.get("Vendas por publicidade (Diretas + Indiretas)", 0)),
                    "receita":      float(rec),
                    "investimento": float(inv),
                    "roas":         round(float(rec) / float(inv), 2) if inv > 0 else 0.0,
                })
        por_campanha.sort(key=lambda x: x["receita"], reverse=True)

    # ── Top 10 anúncios por receita ───────────────────────
    top_anuncios = []
    if "Receita (Moeda local)" in df.columns and "Título do anúncio patrocinado" in df.columns:
        top = df.nlargest(10, "Receita (Moeda local)")
        for _, row in top.iterrows():
            rec = float(row.get("Receita (Moeda local)", 0))
            inv = float(row.get("Investimento (Moeda local)", 0))
            top_anuncios.append({
                "titulo":     str(row.get("Título do anúncio patrocinado", ""))[:80],
                "codigo":     str(row.get("Código do anúncio", "")),
                "status":     str(row.get("Status", "")),
                "campanha":   str(row.get("Campanha", "")),
                "impressoes": int(row.get("Impressões", 0)),
                "cliques":    int(row.get("Cliques", 0)),
                "vendas":     int(row.get("Vendas por publicidade (Diretas + Indiretas)", 0)),
                "receita":    rec,
                "investimento": inv,
                "roas":       round(rec / inv, 2) if inv > 0 else 0.0,
                "cpc":        float(row.get("CPC (Custo por clique)", 0)),
                "ctr":        float(row.get("CTR (Click Through Rate)", 0)),
            })

    print(f"✅ Dados prontos — {len(por_campanha)} campanhas, {len(top_anuncios)} top anúncios")
    print(f"{'='*60}\n")

    return {
        "username":     current_user.username,
        "total_anuncios": int(len(df)),
        "metrics":      metrics,
        "por_campanha": por_campanha,
        "top_anuncios": top_anuncios,
        "source_file":  os.path.basename(parquet_path),
    }