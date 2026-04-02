"""
financial_calculator.py
Calculador centralizado de métricas financeiras.
Todos os cards e tabelas do frontend buscam dados daqui.

Uso:
    from services.financial_calculator import calcular_metricas
    metricas = calcular_metricas(df)
"""
import pandas as pd


# ─────────────────────────────────────────────────────────────
# DEFINIÇÃO DAS COLUNAS
# ─────────────────────────────────────────────────────────────

CREDITOS_COLS = [
    "Receita por produtos (BRL)",
    "Receita por acréscimo no preço (pago pelo comprador)",
    "Receita por envio (BRL)",
]

DEBITOS_COLS = [
    "Taxa de parcelamento equivalente ao acréscimo",
    "Tarifa de venda e impostos (BRL)",
    "Custo de envio com base nas medidas e peso declarados",
    "Custo por diferenças nas medidas e no peso do pacote",
    "Cancelamentos e reembolsos (BRL)",
]

ICMS_COLS = {
    "icms_valor":        "ICMS",
    "icms_difal":        "DIFAL",
    "icms_total_venda":        "ICMS Total",
    "icms_base_calculo": "Base Cálculo ICMS",
    "icms_aliquota":     "Alíquota ICMS (%)",
}

MONEY_COLS = [
    "Receita por produtos (BRL)",
    "Receita por acréscimo no preço (pago pelo comprador)",
    "Taxa de parcelamento equivalente ao acréscimo",
    "Tarifa de venda e impostos (BRL)",
    "Receita por envio (BRL)",
    "Custo de envio com base nas medidas e peso declarados",
    "Custo por diferenças nas medidas e no peso do pacote",
    "Cancelamentos e reembolsos (BRL)",
    "Total (BRL)",
]


# ─────────────────────────────────────────────────────────────
# FUNÇÕES AUXILIARES
# ─────────────────────────────────────────────────────────────

def _fmt(value: float) -> str:
    """Formata float para padrão BR: R$ 1.234,56"""
    return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _safe_sum(df: pd.DataFrame, cols: list) -> float:
    """Soma colunas com segurança, ignorando ausentes"""
    return sum(float(df[col].sum()) for col in cols if col in df.columns)


def _safe_abs_sum(df: pd.DataFrame, cols: list) -> float:
    """Soma o absoluto das colunas (débitos podem ser negativos)"""
    return sum(abs(float(df[col].sum())) for col in cols if col in df.columns)


# ─────────────────────────────────────────────────────────────
# CALCULADOR PRINCIPAL
# ─────────────────────────────────────────────────────────────

def calcular_metricas(df: pd.DataFrame) -> dict:
    """
    Calcula todas as métricas financeiras e de ICMS a partir do DataFrame.

    Args:
        df: DataFrame lido do Parquet (gerado pelo xlsx_processor)

    Returns:
        dict com todas as métricas prontas para uso no frontend
    """

    # ── Totais financeiros ────────────────────────────────────
    total_creditos = _safe_sum(df, CREDITOS_COLS)
    total_debitos  = _safe_abs_sum(df, DEBITOS_COLS)

    # ── Totais de ICMS ────────────────────────────────────────
    total_icms       = float(df["icms_valor"].sum()) if "icms_valor" in df.columns else 0.0
    total_difal      = float(df["icms_difal"].sum()) if "icms_difal" in df.columns else 0.0
    total_icms_total = float(df["icms_total_venda"].sum()) if "icms_total_venda" in df.columns else 0.0

    # ── Débitos totais (operação + ICMS) ──────────────────────
    total_debitos_com_icms = total_debitos + total_icms_total

    # ── Líquido ───────────────────────────────────────────────
    total_liquido          = total_creditos - total_debitos
    total_liquido_com_icms = total_creditos - total_debitos_com_icms

    # ── Total (BRL) acumulado e Líquido Real com Rebate ─────────
    # Total (BRL) = coluna calculada pelo próprio ML por venda
    # Líquido Real com Rebate = Total (BRL) − ICMS Total
    total_brl_acumulado      = float(df["Total (BRL)"].sum()) if "Total (BRL)" in df.columns else 0.0
    liquido_real_com_rebate  = total_brl_acumulado - total_icms_total

    # ── Margens ───────────────────────────────────────────────
    margem                    = (total_liquido_com_icms     / total_creditos * 100) if total_creditos > 0 else 0.0
    perc_icms                 = (total_icms_total           / total_creditos * 100) if total_creditos > 0 else 0.0
    margem_liquido_com_rebate = (liquido_real_com_rebate    / total_creditos * 100) if total_creditos > 0 else 0.0

    # ── Totais por coluna monetária ───────────────────────────
    totals_por_coluna = {}
    for col in MONEY_COLS:
        if col in df.columns:
            # Renomeia "Total (BRL)" para nome mais descritivo
            label = "Total Líquido da Operação com Rebate" if col == "Total (BRL)" else col
            totals_por_coluna[label] = float(df[col].sum())

    # ── Série mensal ──────────────────────────────────────────
    monthly = []
    if "ano_mes" in df.columns:
        group_cols = (
            [c for c in CREDITOS_COLS + DEBITOS_COLS if c in df.columns]
            + [c for c in ICMS_COLS if c in df.columns]
        )
        g = df.groupby("ano_mes")[group_cols].sum().reset_index()

        for _, row in g.iterrows():
            mes_creditos       = sum(row[c] for c in CREDITOS_COLS if c in row)
            mes_debitos        = sum(abs(row[c]) for c in DEBITOS_COLS if c in row)
            mes_icms           = float(row["icms_valor"]) if "icms_valor" in row else 0.0
            mes_difal          = float(row["icms_difal"]) if "icms_difal" in row else 0.0
            mes_icms_total     = float(row["icms_total_venda"]) if "icms_total_venda" in row else 0.0
            mes_debitos_total  = mes_debitos + mes_icms_total
            mes_liquido_sem_rebate        = mes_creditos - mes_debitos_total

            monthly.append({
                "ano_mes":               row["ano_mes"],
                "creditos":              round(mes_creditos, 2),
                "debitos_operacao":      round(mes_debitos, 2),
                "icms":                  round(mes_icms, 2),
                "difal":                 round(mes_difal, 2),
                "icms_total_venda":            round(mes_icms_total, 2),
                "liquido_sem_rebate":               round(mes_liquido_sem_rebate, 2),
            })

    # ── Retorno completo ──────────────────────────────────────
    return {
        # Totais globais
        "total_creditos":           round(total_creditos, 2),
        "total_debitos_operacao":   round(total_debitos, 2),
        "total_icms":               round(total_icms, 2),
        "total_difal":              round(total_difal, 2),
        "total_icms_total":         round(total_icms_total, 2),
        "total_debitos_com_icms":   round(total_debitos_com_icms, 2),
        "total_liquido_sem_rebate":            round(total_liquido_com_icms, 2),

        # Líquido Real com Rebate (Total BRL − ICMS, sem anúncios)
        "total_brl_acumulado":          round(total_brl_acumulado, 2),
        "liquido_real_com_rebate":      round(liquido_real_com_rebate, 2),

        # Margens
        "margem_liquido":               round(margem, 2),
        "margem_liquido_com_rebate":    round(margem_liquido_com_rebate, 2),
        "perc_icms_sobre_receita":      round(perc_icms, 2),

        # Totais por coluna (para o expander)
        "totals_por_coluna":        totals_por_coluna,

        # Série mensal
        "monthly":                  monthly,
    }


def calcular_metricas_mensais_display(monthly: list) -> pd.DataFrame:
    """
    Converte a lista mensal em DataFrame formatado para exibição.
    Ordem das colunas: Mês | Créditos | Débitos da Operação | ICMS | DIFAL | ICMS Total | Líquido

    Args:
        monthly: lista de dicts gerada por calcular_metricas()

    Returns:
        DataFrame formatado com valores em R$ BR
    """
    if not monthly:
        return pd.DataFrame()

    df = pd.DataFrame(monthly).sort_values("ano_mes")

    # Formata valores
    format_cols = {
        "creditos":           "Créditos",
        "debitos_operacao":   "Débitos da Operação",
        "icms":               "ICMS",
        "difal":              "DIFAL",
        "icms_total_venda":         "ICMS Total",
        "liquido_sem_rebate":            "Líquido sem Rebate",
    }

    df_display = pd.DataFrame()
    df_display["Mês"] = df["ano_mes"]

    for col, label in format_cols.items():
        if col in df.columns:
            df_display[label] = df[col].apply(_fmt)

    return df_display