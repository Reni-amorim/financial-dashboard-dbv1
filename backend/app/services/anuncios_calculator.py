"""
anuncios_calculator.py
Calculador centralizado de métricas de anúncios patrocinados.
Todos os cards e tabelas do dashboard de anúncios buscam dados daqui.

Uso:
    from services.anuncios_calculator import calcular_metricas_anuncios
    metricas = calcular_metricas_anuncios(df)
"""
import pandas as pd


# ─────────────────────────────────────────────────────────────
# DEFINIÇÃO DAS COLUNAS
# ─────────────────────────────────────────────────────────────

INT_COLS = [
    "Impressões",
    "Cliques",
    "Vendas diretas",
    "Vendas indiretas",
    "Vendas por publicidade (Diretas + Indiretas)",
]

MONEY_COLS = [
    "Receita (Moeda local)",
    "Investimento (Moeda local)",
    "Receita por vendas diretas (Moeda Local)",
    "Receita por vendas indiretas",
]

PERFORMANCE_COLS = [
    "CTR (Click Through Rate)",
    "CPC  (Custo por clique)",
    "CVR (Conversion rate)",
    "ACOS  (Investimento / Receitas)",
    "ROAS (Receitas / Investimento)",
]

CAMPANHA_AGG_COLS = [
    "Impressões",
    "Cliques",
    "Vendas diretas",
    "Vendas indiretas",
    "Vendas por publicidade (Diretas + Indiretas)",
    "Receita (Moeda local)",
    "Investimento (Moeda local)",
]

TOP_ANUNCIOS_COLS = [
    "Título do anúncio patrocinado",
    "Código do anúncio",
    "Status",
    "Campanha",
    "Impressões",
    "Cliques",
    "Vendas por publicidade (Diretas + Indiretas)",
    "Receita (Moeda local)",
    "Investimento (Moeda local)",
    "CPC  (Custo por clique)",
    "CTR (Click Through Rate)",
]


# ─────────────────────────────────────────────────────────────
# FUNÇÕES AUXILIARES
# ─────────────────────────────────────────────────────────────

def _safe_sum(df: pd.DataFrame, col: str) -> float:
    return float(df[col].sum()) if col in df.columns else 0.0


def _safe_int(df: pd.DataFrame, col: str) -> int:
    return int(df[col].sum()) if col in df.columns else 0


def _safe_mean(df: pd.DataFrame, col: str) -> float:
    return float(df[col].mean()) if col in df.columns and len(df) > 0 else 0.0


def _roas(receita: float, investimento: float) -> float:
    return round(receita / investimento, 2) if investimento > 0 else 0.0


def _acos(investimento: float, receita: float) -> float:
    return round((investimento / receita) * 100, 2) if receita > 0 else 0.0


# ─────────────────────────────────────────────────────────────
# CALCULADOR PRINCIPAL
# ─────────────────────────────────────────────────────────────

def calcular_metricas_anuncios(df: pd.DataFrame) -> dict:
    """
    Calcula todas as métricas de anúncios patrocinados a partir do DataFrame.

    Args:
        df: DataFrame lido do Parquet (gerado pelo anuncios_processor)

    Returns:
        dict com todas as métricas prontas para uso no frontend
    """

    # ── Totais de volume ──────────────────────────────────────
    total_impressoes    = _safe_int(df, "Impressões")
    total_cliques       = _safe_int(df, "Cliques")
    total_vendas        = _safe_int(df, "Vendas por publicidade (Diretas + Indiretas)")
    total_vendas_dir    = _safe_int(df, "Vendas diretas")
    total_vendas_ind    = _safe_int(df, "Vendas indiretas")

    # ── Totais financeiros ────────────────────────────────────
    total_receita       = _safe_sum(df, "Receita (Moeda local)")
    total_investimento  = _safe_sum(df, "Investimento (Moeda local)")
    total_receita_dir   = _safe_sum(df, "Receita por vendas diretas (Moeda Local)")
    total_receita_ind   = _safe_sum(df, "Receita por vendas indiretas")

    # ── KPIs globais ──────────────────────────────────────────
    roas_global = _roas(total_receita, total_investimento)
    acos_global = _acos(total_investimento, total_receita)

    # ── Médias de performance (só anúncios com cliques) ───────
    df_com_cliques = df[df["Cliques"] > 0] if "Cliques" in df.columns else df
    ctr_medio  = _safe_mean(df_com_cliques, "CTR (Click Through Rate)")
    cpc_medio  = _safe_mean(df_com_cliques, "CPC  (Custo por clique)")
    cvr_medio  = _safe_mean(df_com_cliques, "CVR (Conversion rate)")
    acos_medio = _safe_mean(df_com_cliques, "ACOS  (Investimento / Receitas)")
    roas_medio = _safe_mean(df_com_cliques, "ROAS (Receitas / Investimento)")

    # ── Contagem por status ───────────────────────────────────
    status_counts = {}
    if "Status" in df.columns:
        status_counts = {k: int(v) for k, v in df["Status"].value_counts().to_dict().items()}

    # ── Agrupado por campanha ─────────────────────────────────
    por_campanha = []
    if "Campanha" in df.columns:
        agg = {col: "sum" for col in CAMPANHA_AGG_COLS if col in df.columns}
        if agg:
            g = df.groupby("Campanha").agg(agg).reset_index()
            for _, row in g.iterrows():
                rec = float(row.get("Receita (Moeda local)", 0))
                inv = float(row.get("Investimento (Moeda local)", 0))
                por_campanha.append({
                    "campanha":     row["Campanha"],
                    "impressoes":   int(row.get("Impressões", 0)),
                    "cliques":      int(row.get("Cliques", 0)),
                    "vendas":       int(row.get("Vendas por publicidade (Diretas + Indiretas)", 0)),
                    "receita":      rec,
                    "investimento": inv,
                    "roas":         _roas(rec, inv),
                    "acos":         _acos(inv, rec),
                })
            por_campanha.sort(key=lambda x: x["receita"], reverse=True)

    # ── Top 10 anúncios por receita ───────────────────────────
    top_anuncios = []
    if "Receita (Moeda local)" in df.columns and "Título do anúncio patrocinado" in df.columns:
        top = df.nlargest(10, "Receita (Moeda local)")
        for _, row in top.iterrows():
            rec = float(row.get("Receita (Moeda local)", 0))
            inv = float(row.get("Investimento (Moeda local)", 0))
            top_anuncios.append({
                "titulo":       str(row.get("Título do anúncio patrocinado", ""))[:80],
                "codigo":       str(row.get("Código do anúncio", "")),
                "status":       str(row.get("Status", "")),
                "campanha":     str(row.get("Campanha", "")),
                "impressoes":   int(row.get("Impressões", 0)),
                "cliques":      int(row.get("Cliques", 0)),
                "vendas":       int(row.get("Vendas por publicidade (Diretas + Indiretas)", 0)),
                "receita":      rec,
                "investimento": inv,
                "roas":         _roas(rec, inv),
                "cpc":          float(row.get("CPC  (Custo por clique)", 0)),
                "ctr":          float(row.get("CTR (Click Through Rate)", 0)),
            })

    # ── Retorno completo ──────────────────────────────────────
    return {
        # Volume
        "total_anuncios":           int(len(df)),
        "status_counts":            status_counts,
        "total_impressoes":         total_impressoes,
        "total_cliques":            total_cliques,
        "total_vendas":             total_vendas,
        "total_vendas_diretas":     total_vendas_dir,
        "total_vendas_indiretas":   total_vendas_ind,

        # Financeiro
        "total_receita":            round(total_receita, 2),
        "total_investimento":       round(total_investimento, 2),
        "total_receita_direta":     round(total_receita_dir, 2),
        "total_receita_indireta":   round(total_receita_ind, 2),

        # KPIs globais
        "roas_global":              roas_global,
        "acos_global":              acos_global,

        # Médias de performance
        "ctr_medio":                round(ctr_medio, 4),
        "cpc_medio":                round(cpc_medio, 4),
        "cvr_medio":                round(cvr_medio, 4),
        "acos_medio":               round(acos_medio, 4),
        "roas_medio":               round(roas_medio, 4),

        # Agrupamentos
        "por_campanha":             por_campanha,
        "top_anuncios":             top_anuncios,
    }