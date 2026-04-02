"""
analitico_calculator.py
Calculador centralizado do Dashboard Analítico.
Cruza faturamento × anúncios e retorna todas as métricas prontas.

Uso:
    from services.analitico_calculator import calcular_analitico
    result = calcular_analitico(df_fat, df_anun, page=1, page_size=100)
"""
import pandas as pd
from app.services.financial_calculator import CREDITOS_COLS, DEBITOS_COLS


# ─────────────────────────────────────────────────────────────
# COLUNAS DE REFERÊNCIA
# ─────────────────────────────────────────────────────────────

# Candidatos para coluna de MLB no faturamento
MLB_FAT_CANDIDATES = [
    "# de anúncio",
    "Código do anúncio",
    "Número do anúncio",
    "ID do anúncio",
    "Código ML",
]

# Colunas do parquet de anúncios
COL_MLB_ANUN    = "Código do anúncio"
COL_TITULO_ANUN = "Título do anúncio patrocinado"
COL_INVEST      = "Investimento (Moeda local)"
COL_VENDAS_DIR  = "Vendas diretas"


# ─────────────────────────────────────────────────────────────
# FUNÇÕES AUXILIARES
# ─────────────────────────────────────────────────────────────

def _safe_float(val) -> float:
    try:
        return float(val or 0)
    except Exception:
        return 0.0


def _format_date(val) -> str:
    """Converte Timestamp/string/NaT para DD/MM/YYYY legível."""
    if val is None:
        return ""
    try:
        ts = pd.to_datetime(val, errors="coerce")
        if pd.isna(ts):
            return ""
        return ts.strftime("%d/%m/%Y")
    except Exception:
        s = str(val)
        return "" if s in ("NaT", "nan", "None", "") else s[:10]


def _sum_cols(df: pd.DataFrame, cols: list) -> float:
    return sum(float(df[c].sum()) for c in cols if c in df.columns)


def _abs_sum_cols(df: pd.DataFrame, cols: list) -> float:
    return sum(abs(float(df[c].sum())) for c in cols if c in df.columns)


# ─────────────────────────────────────────────────────────────
# CALCULADOR PRINCIPAL
# ─────────────────────────────────────────────────────────────

def calcular_analitico(
    df_fat: pd.DataFrame,
    df_anun: pd.DataFrame,
    page: int = 1,
    page_size: int = 100,
    filtro_mlb: str = "",
) -> dict:
    """
    Cruza faturamento com anúncios patrocinados e calcula todas as métricas.

    Estratégia de rateio:
        custo_por_venda = investimento_anuncio / vendas_diretas
        liquido_real    = Total (BRL) do ML − custo_por_venda

    Args:
        df_fat:     DataFrame do parquet de faturamento
        df_anun:    DataFrame do parquet de anúncios
        page:       Página atual para paginação das vendas
        page_size:  Tamanho da página
        filtro_mlb: Filtro opcional por código MLB

    Returns:
        dict com summary, acumulado, vendas paginadas e paginacao
    """

    # ── Totais financeiros (via financial_calculator) ─────────
    total_creditos = _sum_cols(df_fat, CREDITOS_COLS)
    total_debitos  = _abs_sum_cols(df_fat, DEBITOS_COLS)
    total_liquido  = total_creditos - total_debitos

    # ── ICMS (se existir no parquet) ──────────────────────────
    total_icms_total = float(df_fat["icms_total_venda"].sum()) if "icms_total_venda" in df_fat.columns else 0.0
    total_debitos_com_icms = total_debitos + total_icms_total
    total_liquido_com_icms = total_creditos - total_debitos_com_icms

    # ── Período ───────────────────────────────────────────────
    periodo_inicio = ""
    periodo_fim    = ""
    if "Data da venda" in df_fat.columns:
        datas = pd.to_datetime(df_fat["Data da venda"], errors="coerce").dropna()
        if not datas.empty:
            periodo_inicio = datas.min().strftime("%d/%m/%Y")
            periodo_fim    = datas.max().strftime("%d/%m/%Y")

    total_vendas = int(len(df_fat))

    # ── Acumulado por MLB (anúncios) ──────────────────────────
    acumulado_mlb = {}

    if COL_MLB_ANUN in df_anun.columns and COL_INVEST in df_anun.columns:
        for _, row in df_anun.iterrows():
            mlb    = str(row.get(COL_MLB_ANUN, "")).strip()
            inv    = _safe_float(row.get(COL_INVEST, 0))
            vd     = int(row.get(COL_VENDAS_DIR, 0) or 0)
            titulo = str(row.get(COL_TITULO_ANUN, "")).strip()

            if not mlb or mlb in ("nan", "None", ""):
                continue

            if mlb not in acumulado_mlb:
                acumulado_mlb[mlb] = {"investimento": 0.0, "vendas": 0, "titulo": titulo}
            acumulado_mlb[mlb]["investimento"] += inv
            acumulado_mlb[mlb]["vendas"]       += vd

    # Custo por venda para cada MLB
    for mlb, info in acumulado_mlb.items():
        inv = info["investimento"]
        vd  = info["vendas"]
        info["custo_por_venda"] = round(inv / vd, 4) if vd > 0 else round(inv, 4)

    total_anuncios = sum(v["investimento"] for v in acumulado_mlb.values())

    # ── Total de cancelamentos e reembolsos ───────────────────
    total_cancelamentos = abs(float(df_fat["Cancelamentos e reembolsos (BRL)"].sum())) if "Cancelamentos e reembolsos (BRL)" in df_fat.columns else 0.0

    # ── Coluna MLB no faturamento ─────────────────────────────
    mlb_col_fat = next(
        (c for c in MLB_FAT_CANDIDATES if c in df_fat.columns), None
    )

    # ── Cruzamento linha a linha ──────────────────────────────
    vendas_rows         = []
    custo_total_rateado = 0.0

    for _, row in df_fat.iterrows():
        mlb_fat = ""
        if mlb_col_fat:
            raw = row.get(mlb_col_fat, "")
            if str(raw) not in ("nan", "None", "", "NaT"):
                mlb_fat = str(raw).strip()

        custo_venda = 0.0
        if mlb_fat and mlb_fat in acumulado_mlb:
            custo_venda = acumulado_mlb[mlb_fat]["custo_por_venda"]

        receita_produto  = _safe_float(row.get("Receita por produtos (BRL)", 0))
        tarifa_venda     = _safe_float(row.get("Tarifa de venda e impostos (BRL)", 0))
        receita_envio    = _safe_float(row.get("Receita por envio (BRL)", 0))
        custo_envio      = _safe_float(row.get("Custo de envio com base nas medidas e peso declarados", 0))
        total_ml         = _safe_float(row.get("Total (BRL)", 0))
        icms_linha       = _safe_float(row.get("icms_total_venda", 0))

        # Líquido Operação sem Rebate = receita produto + tarifa venda + receita envio + custo envio
        liquido_operacao_sem_rebate      = receita_produto + tarifa_venda + receita_envio + custo_envio
        # Líquido Operação sem Rebate − ICMS − Custo Anúncio
        liquido_operacao_sem_rebate_icms = liquido_operacao_sem_rebate - icms_linha - custo_venda

        # Líquido Real com Rebate = Total (BRL) − ICMS − custo anúncio
        liquido_real_com_rebate = total_ml - custo_venda - icms_linha

        custo_total_rateado += custo_venda

        vendas_rows.append({
            "N.º de venda":                    str(row.get("N.º de venda", "")),
            "Data da venda":                   _format_date(row.get("Data da venda")),
            "mlb":                             mlb_fat,
            "Título do anúncio":               str(row.get("Título do anúncio", ""))[:80],
            "Variação":                        str(row.get("Variação", "")),
            "Unidades":                        str(row.get("Unidades", "")),
            "Receita por produtos (BRL)":      receita_produto,
            "Total (BRL)":                     total_ml,
            "icms_total_venda":                icms_linha,
            "custo_por_venda":                 custo_venda,
            "liquido_operacao_sem_rebate":      liquido_operacao_sem_rebate,
            "liquido_operacao_sem_rebate_icms": liquido_operacao_sem_rebate_icms,
            "liquido_real_com_rebate":          liquido_real_com_rebate,
        })

    # Fallback: sem coluna MLB → distribui proporcionalmente
    if not mlb_col_fat and total_vendas > 0:
        custo_medio = total_anuncios / total_vendas
        for vrow in vendas_rows:
            vrow["custo_por_venda"]                 = custo_medio
            vrow["liquido_real_com_rebate"]          = vrow["Total (BRL)"] - custo_medio - vrow["icms_total_venda"]
            vrow["liquido_operacao_sem_rebate_icms"] = vrow["liquido_operacao_sem_rebate"] - vrow["icms_total_venda"] - custo_medio
        custo_total_rateado = total_anuncios

    # ── Total (BRL) acumulado — soma da coluna Total (BRL) do faturamento ──
    total_brl_acumulado = float(df_fat["Total (BRL)"].sum()) if "Total (BRL)" in df_fat.columns else 0.0

    # ── Líquido Real global (sem rebate) ──────────────────────
    liquido_real_global = total_liquido_com_icms - total_anuncios

    # ── Líquido Real com Rebate ───────────────────────────────
    # Fórmula: Total (BRL) acumulado − ICMS Total − Gasto com Anúncios
    liquido_real_com_rebate_global = total_brl_acumulado - total_icms_total - total_anuncios

    margem_original         = round((total_liquido_com_icms    / total_creditos * 100), 2) if total_creditos > 0 else 0.0
    margem_real             = round((liquido_real_global        / total_creditos * 100), 2) if total_creditos > 0 else 0.0
    margem_real_com_rebate  = round((liquido_real_com_rebate_global    / total_creditos * 100), 2) if total_creditos > 0 else 0.0

    # ── Summary ───────────────────────────────────────────────
    summary = {
        "total_creditos":           round(total_creditos, 2),
        "total_debitos":            round(total_debitos_com_icms, 2),
        "total_debitos_op":         round(total_debitos, 2),
        "total_icms":               round(total_icms_total, 2),
        "total_liquido_sem_rebate": round(total_liquido_com_icms, 2),
        "total_anuncios":           round(total_anuncios, 2),
        "liquido_real":             round(liquido_real_global, 2),
        "total_brl_acumulado":      round(total_brl_acumulado, 2),
        "liquido_real_com_rebate":  round(liquido_real_com_rebate_global, 2),
        "margem_original":          margem_original,
        "margem_real":              margem_real,
        "margem_real_com_rebate":   margem_real_com_rebate,
        "total_cancelamentos":      round(total_cancelamentos, 2),
        "total_vendas":             total_vendas,
        "periodo_inicio":           periodo_inicio,
        "periodo_fim":              periodo_fim,
    }

    # ── Acumulado list ────────────────────────────────────────
    acumulado_list = [
        {
            "mlb":                mlb,
            "titulo":             info["titulo"],
            "investimento_total": round(info["investimento"], 2),
            "vendas_diretas":     info["vendas"],
            "custo_por_venda":    info["custo_por_venda"],
        }
        for mlb, info in sorted(acumulado_mlb.items(), key=lambda x: -x[1]["investimento"])
        if info["investimento"] > 0
    ]

    # ── Paginação + filtro ────────────────────────────────────
    if filtro_mlb:
        vendas_rows = [v for v in vendas_rows if filtro_mlb.upper() in v["mlb"].upper()]

    total_filtrado = len(vendas_rows)
    inicio         = (page - 1) * page_size
    vendas_pag     = vendas_rows[inicio: inicio + page_size]

    return {
        "summary":   summary,
        "acumulado": acumulado_list,
        "vendas":    vendas_pag,
        "paginacao": {
            "page":        page,
            "page_size":   page_size,
            "total":       total_filtrado,
            "total_pages": -(-total_filtrado // page_size),
        },
    }