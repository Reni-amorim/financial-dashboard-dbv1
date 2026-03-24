"""
Dashboard Analítico — cruza faturamento com anúncios patrocinados
Endpoint: GET /api/v1/dashboard/analitico
          GET /api/v1/dashboard/analitico/exportar
"""
import os
import io
import base64
import json
from glob import glob
from datetime import date

import pandas as pd
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.database import get_db
from app.models.user import User

router = APIRouter(prefix="/api/v1/dashboard/analitico", tags=["dashboard-analitico"])

# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def _latest_parquet(user_id: int, tipo: str) -> str | None:
    pattern = os.path.join("data", tipo, str(user_id), "*.parquet")
    files = glob(pattern)
    if not files:
        return None
    files.sort(key=os.path.getmtime, reverse=True)
    return files[0]


def _to_money(series: pd.Series) -> pd.Series:
    """Converte coluna para float (já processado no parquet, mas por segurança)."""
    return pd.to_numeric(series, errors="coerce").fillna(0.0)


# ─────────────────────────────────────────────
# Colunas de faturamento
# ─────────────────────────────────────────────

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


# ─────────────────────────────────────────────
# Lógica de cruzamento
# ─────────────────────────────────────────────

def _build_analitico(df_fat: pd.DataFrame, df_anun: pd.DataFrame, page: int = 1, page_size: int = 100, filtro_mlb: str = "") -> dict:
    """
    Cruza faturamento com anúncios patrocinados pelo Código MLB.

    Estratégia de rateio:
    - Cada anúncio tem um investimento total e N vendas diretas no período.
    - Custo por venda = investimento / vendas_diretas (ou investimento se 0 vendas).
    - Para cada linha de faturamento que tiver um MLB com anúncio ativo,
      atribuímos o custo_por_venda proporcional.
    """

    # ── Faturamento ──────────────────────────────────────
    total_creditos = sum(
        df_fat[c].sum() for c in CREDITOS_COLS if c in df_fat.columns
    )
    total_debitos = sum(
        abs(df_fat[c].sum()) for c in DEBITOS_COLS if c in df_fat.columns
    )
    total_liquido = total_creditos - total_debitos

    # Período
    periodo_inicio = ""
    periodo_fim = ""
    if "Data da venda" in df_fat.columns:
        datas = pd.to_datetime(df_fat["Data da venda"], errors="coerce").dropna()
        if not datas.empty:
            periodo_inicio = datas.min().strftime("%d/%m/%Y")
            periodo_fim    = datas.max().strftime("%d/%m/%Y")

    total_vendas = int(len(df_fat))

    # ── Anúncios: acumulado por MLB ───────────────────────
    # Colunas do parquet de anúncios
    COL_MLB        = "Código do anúncio"
    COL_TITULO     = "Título do anúncio patrocinado"
    COL_INVEST     = "Investimento (Moeda local)"
    COL_VENDAS_DIR = "Vendas diretas"

    acumulado_mlb = {}   # mlb → {investimento, vendas_diretas, titulo}

    if COL_MLB in df_anun.columns and COL_INVEST in df_anun.columns:
        for _, row in df_anun.iterrows():
            mlb   = str(row.get(COL_MLB, "")).strip()
            inv   = float(row.get(COL_INVEST, 0) or 0)
            vd    = int(row.get(COL_VENDAS_DIR, 0) or 0)
            titulo = str(row.get(COL_TITULO, "")).strip()

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

    # ── Cruzamento linha a linha ───────────────────────────
    # No faturamento ML a coluna com código MLB chama "Código do anúncio"
    MLB_FAT_CANDIDATES = [
        "# de anúncio",        # nome real no relatório de faturamento ML
        "Código do anúncio",
        "Número do anúncio",
        "ID do anúncio",
        "Código ML",
    ]
    mlb_col_fat = next(
        (c for c in MLB_FAT_CANDIDATES if c in df_fat.columns), None
    )

    print(f"   Coluna MLB no faturamento: {mlb_col_fat!r}")
    print(f"   Colunas do faturamento: {list(df_fat.columns)}")

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

    vendas_rows = []
    custo_total_rateado = 0.0

    for _, row in df_fat.iterrows():
        # MLB: filtra valores nulos explicitamente
        mlb_fat = ""
        if mlb_col_fat:
            raw_mlb = row.get(mlb_col_fat, "")
            if str(raw_mlb) not in ("nan", "None", "", "NaT"):
                mlb_fat = str(raw_mlb).strip()

        custo_venda = 0.0
        if mlb_fat and mlb_fat in acumulado_mlb:
            custo_venda = acumulado_mlb[mlb_fat]["custo_por_venda"]

        receita_produto = float(row.get("Receita por produtos (BRL)", 0) or 0)
        # Total (BRL) = resultado líquido calculado pelo próprio ML após todas as
        # taxas deles — NÃO inclui custo de anúncios patrocinados
        total_ml     = float(row.get("Total (BRL)", 0) or 0)
        # Líquido Real = Líquido ML − Custo Anúncio
        # (Total BRL já descontou taxas ML, só falta descontar o anúncio)
        liquido_real = total_ml - custo_venda

        custo_total_rateado += custo_venda

        vrow = {
            "N.º de venda":               str(row.get("N.º de venda", "")),
            "Data da venda":              _format_date(row.get("Data da venda")),
            "mlb":                        mlb_fat,
            "Título do anúncio":          str(row.get("Título do anúncio", ""))[:80],
            "Variação":                   str(row.get("Variação", "")),
            "Unidades":                   str(row.get("Unidades", "")),
            "Receita por produtos (BRL)": receita_produto,
            "Total (BRL)":                total_ml,
            "custo_por_venda":            custo_venda,
            "liquido_real":               liquido_real,
        }
        vendas_rows.append(vrow)

    # Se não achou coluna MLB no faturamento, distribui investimento total
    # proporcionalmente entre todas as vendas
    if not mlb_col_fat and total_vendas > 0:
        custo_por_venda_medio = total_anuncios / total_vendas
        for vrow in vendas_rows:
            vrow["custo_por_venda"] = custo_por_venda_medio
            vrow["liquido_real"] = vrow["Receita por produtos (BRL)"] - custo_por_venda_medio
        custo_total_rateado = total_anuncios

    liquido_real = total_liquido - total_anuncios
    margem_original = round((total_liquido / total_creditos * 100), 2) if total_creditos > 0 else 0.0
    margem_real     = round((liquido_real   / total_creditos * 100), 2) if total_creditos > 0 else 0.0

    summary = {
        "total_creditos":  float(total_creditos),
        "total_debitos":   float(total_debitos),
        "total_liquido":   float(total_liquido),
        "total_anuncios":  float(total_anuncios),
        "liquido_real":    float(liquido_real),
        "margem_original": margem_original,
        "margem_real":     margem_real,
        "total_vendas":    total_vendas,
        "periodo_inicio":  periodo_inicio,
        "periodo_fim":     periodo_fim,
    }

    acumulado_list = [
        {
            "mlb":               mlb,
            "titulo":            info["titulo"],
            "investimento_total": round(info["investimento"], 2),
            "vendas_diretas":    info["vendas"],
            "custo_por_venda":   info["custo_por_venda"],
        }
        for mlb, info in sorted(acumulado_mlb.items(), key=lambda x: -x[1]["investimento"])
        if info["investimento"] > 0
    ]

    # Paginação + filtro opcional por MLB
    if filtro_mlb:
        vendas_rows = [v for v in vendas_rows if filtro_mlb.upper() in v["mlb"].upper()]

    total_vendas_filtradas = len(vendas_rows)
    inicio = (page - 1) * page_size
    fim    = inicio + page_size
    vendas_paginadas = vendas_rows[inicio:fim]

    return {
        "summary":    summary,
        "acumulado":  acumulado_list,
        "vendas":     vendas_paginadas,
        "paginacao": {
            "page":        page,
            "page_size":   page_size,
            "total":       total_vendas_filtradas,
            "total_pages": -(-total_vendas_filtradas // page_size),  # ceil
        },
    }


# ─────────────────────────────────────────────
# Endpoints
# ─────────────────────────────────────────────

@router.get("/")
def get_dashboard_analitico(
    page: int = 1,
    page_size: int = 100,
    mlb: str = "",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retorna análise cruzada faturamento × anúncios patrocinados"""

    parquet_fat  = _latest_parquet(current_user.id, "faturamento")
    parquet_anun = _latest_parquet(current_user.id, "anuncios")

    if not parquet_fat and not parquet_anun:
        return {
            "message": "Faça upload da planilha de faturamento e de anúncios para ver a análise cruzada.",
            "summary": {}, "acumulado": [], "vendas": [],
        }

    if not parquet_fat:
        return {
            "message": "Faça upload da planilha de faturamento para cruzar com os anúncios.",
            "summary": {}, "acumulado": [], "vendas": [],
        }

    if not parquet_anun:
        return {
            "message": "Faça upload da planilha de anúncios patrocinados para cruzar com o faturamento.",
            "summary": {}, "acumulado": [], "vendas": [],
        }

    df_fat  = pd.read_parquet(parquet_fat)
    df_anun = pd.read_parquet(parquet_anun)

    print(f"\n{'='*60}")
    print(f"🔬 DASHBOARD ANALÍTICO")
    print(f"   Faturamento: {len(df_fat)} linhas")
    print(f"   Anúncios:    {len(df_anun)} linhas")
    print(f"{'='*60}")

    result = _build_analitico(df_fat, df_anun, page=page, page_size=page_size, filtro_mlb=mlb)

    print(f"   Créditos:      R$ {result['summary']['total_creditos']:,.2f}")
    print(f"   Débitos:       R$ {result['summary']['total_debitos']:,.2f}")
    print(f"   Líquido:       R$ {result['summary']['total_liquido']:,.2f}")
    print(f"   Anúncios:      R$ {result['summary']['total_anuncios']:,.2f}")
    print(f"   Líquido Real:  R$ {result['summary']['liquido_real']:,.2f}")
    print(f"   Margem Real:   {result['summary']['margem_real']:.1f}%")
    print(f"{'='*60}\n")

    return {
        "username": current_user.username,
        **result,
    }


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
    result  = _build_analitico(df_fat, df_anun)

    summary   = result["summary"]
    acumulado = result["acumulado"]
    vendas    = result["vendas"]

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:

        # Aba 1: Resumo
        df_resumo = pd.DataFrame([{
            "Métrica":                 k,
            "Valor":                   v,
        } for k, v in summary.items()])
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

    today = date.today().strftime("%Y%m%d")
    filename = f"relatorio_analitico_{today}.xlsx"

    return {
        "filename": filename,
        "data":     xlsx_b64,
    }