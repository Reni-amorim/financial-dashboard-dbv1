"""
Processador de planilha de Anúncios Patrocinados - Mercado Livre
Campos baseados no relatório real: 'Relatório Anúncios patrocinados'
"""
import os
import uuid
import pandas as pd


# ─────────────────────────────────────────────
# Configuração da planilha
# ─────────────────────────────────────────────

ANUNCIOS_SHEET = "Relatório Anúncios patrocinados"
ANUNCIOS_HEADER_ROW = 1
ANUNCIOS_KEY_HEADER = "Título do anúncio patrocinado"

NULL_VALUES = {"-", "", "nan", "None", "NaN", "N/A", "0"}

DATE_COLS = ["Desde", "Até"]

TEXT_COLS = [
    "Campanha",
    "Título do anúncio patrocinado",
    "Código do anúncio",
    "Status",
]

INT_COLS = [
    "Impressões",
    "Cliques",
    "Vendas diretas",
    "Vendas indiretas",
    "Vendas por publicidade (Diretas + Indiretas)",
]

FLOAT_COLS = [
    "CPC (Custo por clique)",
    "CTR (Click Through Rate)",
    "CVR (Conversion rate)",
    "ACOS (Investimento / Receitas)",
    "ROAS (Receitas / Investimento)",
]

MONEY_COLS = [
    "Receita (Moeda local)",
    "Investimento (Moeda local)",
    "Receita por vendas diretas (Moeda Local)",
    "Receita por vendas indiretas",
]


# ─────────────────────────────────────────────
# Funções de conversão
# ─────────────────────────────────────────────

def _to_int(series: pd.Series) -> pd.Series:
    def clean(val):
        if isinstance(val, (int, float)):
            return 0 if pd.isna(val) else str(int(val))
        val = str(val).strip()
        if val in NULL_VALUES:
            return "0"
        val = val.replace(".", "").replace(",", "")
        val = "".join(c for c in val if c.isdigit() or c == "-")
        return val if val else "0"
    return pd.to_numeric(series.apply(clean), errors="coerce").fillna(0).astype(int)


def _to_float(series: pd.Series) -> pd.Series:
    def clean(val):
        if isinstance(val, (int, float)):
            return 0.0 if pd.isna(val) else float(val)
        val = str(val).strip()
        if val in NULL_VALUES:
            return 0.0
        val = val.replace(",", ".")
        try:
            return float(val)
        except ValueError:
            return 0.0
    return series.apply(clean).astype(float)


def _to_money(series: pd.Series) -> pd.Series:
    def clean(val):
        if isinstance(val, (int, float)):
            return 0.0 if pd.isna(val) else float(val)
        val = str(val).strip()
        if val in {"-", "", "nan", "None", "NaN", "N/A"}:
            return 0.0
        val = val.replace("R$", "").replace("\u00a0", "").replace(" ", "").strip()
        if not val:
            return 0.0
        num_dots = val.count(".")
        num_commas = val.count(",")
        if num_commas > 0 and num_dots > 0:
            val = val.replace(".", "").replace(",", ".")
        elif num_commas > 0 and num_dots == 0:
            val = val.replace(",", ".")
        val = "".join(c for c in val if c.isdigit() or c in ".-")
        try:
            return float(val)
        except ValueError:
            return 0.0
    return series.apply(clean).astype(float)


def _to_date(series: pd.Series) -> pd.Series:
    _PT_MONTHS = {
        "jan": "Jan", "fev": "Feb", "mar": "Mar", "abr": "Apr",
        "mai": "May", "jun": "Jun", "jul": "Jul", "ago": "Aug",
        "set": "Sep", "out": "Oct", "nov": "Nov", "dez": "Dec",
    }

    def _parse(val):
        if pd.isna(val):
            return pd.NaT
        s = str(val).strip().lower()
        for pt, en in _PT_MONTHS.items():
            s = s.replace(pt, en)
        try:
            return pd.to_datetime(s, format="%d-%b-%Y")
        except Exception:
            return pd.to_datetime(val, dayfirst=True, errors="coerce")

    return series.apply(_parse)


def _normalize_status(series: pd.Series) -> pd.Series:
    return series.fillna("Sem status").str.strip()


def _dedupe_columns(cols: list) -> list:
    seen = {}
    out = []
    for c in cols:
        c = str(c).strip()
        if c not in seen:
            seen[c] = 1
            out.append(c)
        else:
            seen[c] += 1
            out.append(f"{c}__{seen[c]}")
    return out


# ─────────────────────────────────────────────
# Leitura
# ─────────────────────────────────────────────

def read_anuncios_table(xlsx_path: str) -> pd.DataFrame:
    """Lê a planilha de anúncios patrocinados."""
    try:
        df = pd.read_excel(
            xlsx_path,
            sheet_name=ANUNCIOS_SHEET,
            header=ANUNCIOS_HEADER_ROW,
            dtype=str,
        )
    except Exception:
        # fallback: sem especificar aba
        df = pd.read_excel(xlsx_path, header=ANUNCIOS_HEADER_ROW, dtype=str)

    # Normaliza nomes — remove \n e espaços extras
    df.columns = [
        " ".join(str(c).replace("\n", " ").replace("\u00a0", " ").strip().split())
        for c in df.columns
    ]

    if ANUNCIOS_KEY_HEADER not in df.columns:
        # Fallback: busca linha por linha
        preview = pd.read_excel(xlsx_path, sheet_name=ANUNCIOS_SHEET, header=None, nrows=20, dtype=str)
        header_row = None
        for i in range(len(preview)):
            row = preview.iloc[i].tolist()
            if any(ANUNCIOS_KEY_HEADER in str(cell) for cell in row):
                header_row = i
                break
        if header_row is None:
            raise ValueError(f"Cabeçalho '{ANUNCIOS_KEY_HEADER}' não encontrado")
        df = pd.read_excel(xlsx_path, sheet_name=ANUNCIOS_SHEET, header=header_row, dtype=str)
        df.columns = [
            " ".join(str(c).replace("\n", " ").replace("\u00a0", " ").strip().split())
            for c in df.columns
        ]
        print(f"✅ Cabeçalho encontrado na linha {header_row} (fallback)")

    df = df.dropna(axis=1, how="all").dropna(how="all")
    df.columns = _dedupe_columns(list(df.columns))
    return df


# ─────────────────────────────────────────────
# Processamento principal
# ─────────────────────────────────────────────

def process_anuncios_to_parquet(xlsx_path: str, user_id: int) -> dict:
    """
    Lê, limpa, tipifica e salva em Parquet a planilha de anúncios patrocinados.
    """
    df = read_anuncios_table(xlsx_path)

    print(f"\n{'='*60}")
    print(f"📢 PROCESSANDO PLANILHA DE ANÚNCIOS PATROCINADOS")
    print(f"{'='*60}")
    print(f"📊 Linhas brutas: {len(df)}")
    print(f"   Colunas: {list(df.columns)}")

    # Datas
    for col in DATE_COLS:
        if col in df.columns:
            df[col] = _to_date(df[col])

    # Status
    if "Status" in df.columns:
        df["Status"] = _normalize_status(df["Status"])

    # Inteiros
    for col in INT_COLS:
        if col in df.columns:
            df[col] = _to_int(df[col])

    # Floats (métricas %)
    for col in FLOAT_COLS:
        if col in df.columns:
            df[col] = _to_float(df[col])

    # Monetários
    for col in MONEY_COLS:
        if col in df.columns:
            df[col] = _to_money(df[col])
            print(f"   💰 {col}: R$ {df[col].sum():,.2f}")

    # Coluna auxiliar
    if "Campanha" in df.columns and "Desde" in df.columns:
        df["campanha_periodo"] = (
            df["Campanha"].fillna("") + " | " +
            df["Desde"].dt.strftime("%d/%m/%Y").fillna("")
        )

    # ── Métricas ──
    ativos       = int((df["Status"] == "Ativo").sum()) if "Status" in df.columns else 0
    desativados  = int((df["Status"] == "Desativada").sum()) if "Status" in df.columns else 0
    movidos      = int((df["Status"] == "Movido").sum()) if "Status" in df.columns else 0

    total_impressoes   = int(df["Impressões"].sum()) if "Impressões" in df.columns else 0
    total_cliques      = int(df["Cliques"].sum()) if "Cliques" in df.columns else 0
    total_vendas_dir   = int(df["Vendas diretas"].sum()) if "Vendas diretas" in df.columns else 0
    total_vendas_ind   = int(df["Vendas indiretas"].sum()) if "Vendas indiretas" in df.columns else 0
    total_vendas       = int(df["Vendas por publicidade (Diretas + Indiretas)"].sum()) if "Vendas por publicidade (Diretas + Indiretas)" in df.columns else 0

    total_receita      = float(df["Receita (Moeda local)"].sum()) if "Receita (Moeda local)" in df.columns else 0.0
    total_investimento = float(df["Investimento (Moeda local)"].sum()) if "Investimento (Moeda local)" in df.columns else 0.0
    total_receita_dir  = float(df["Receita por vendas diretas (Moeda Local)"].sum()) if "Receita por vendas diretas (Moeda Local)" in df.columns else 0.0
    total_receita_ind  = float(df["Receita por vendas indiretas"].sum()) if "Receita por vendas indiretas" in df.columns else 0.0

    df_com_cliques = df[df["Cliques"] > 0] if "Cliques" in df.columns else df
    ctr_medio  = float(df_com_cliques["CTR (Click Through Rate)"].mean()) if "CTR (Click Through Rate)" in df_com_cliques.columns and len(df_com_cliques) > 0 else 0.0
    cvr_medio  = float(df_com_cliques["CVR (Conversion rate)"].mean()) if "CVR (Conversion rate)" in df_com_cliques.columns and len(df_com_cliques) > 0 else 0.0
    cpc_medio  = float(df_com_cliques["CPC (Custo por clique)"].mean()) if "CPC (Custo por clique)" in df_com_cliques.columns and len(df_com_cliques) > 0 else 0.0
    acos_medio = float(df_com_cliques["ACOS (Investimento / Receitas)"].mean()) if "ACOS (Investimento / Receitas)" in df_com_cliques.columns and len(df_com_cliques) > 0 else 0.0
    roas_medio = float(df_com_cliques["ROAS (Receitas / Investimento)"].mean()) if "ROAS (Receitas / Investimento)" in df_com_cliques.columns and len(df_com_cliques) > 0 else 0.0

    roas_global = round(total_receita / total_investimento, 2) if total_investimento > 0 else 0.0
    acos_global = round((total_investimento / total_receita) * 100, 2) if total_receita > 0 else 0.0

    metrics = {
        "total_anuncios":       int(len(df)),
        "anuncios_ativos":      ativos,
        "anuncios_desativados": desativados,
        "anuncios_movidos":     movidos,
        "total_impressoes":     total_impressoes,
        "total_cliques":        total_cliques,
        "total_vendas":         total_vendas,
        "total_vendas_diretas": total_vendas_dir,
        "total_vendas_indiretas": total_vendas_ind,
        "total_receita":        total_receita,
        "total_investimento":   total_investimento,
        "total_receita_direta": total_receita_dir,
        "total_receita_indireta": total_receita_ind,
        "ctr_medio":   round(ctr_medio, 4),
        "cvr_medio":   round(cvr_medio, 4),
        "cpc_medio":   round(cpc_medio, 4),
        "acos_medio":  round(acos_medio, 4),
        "roas_medio":  round(roas_medio, 4),
        "roas_global": roas_global,
        "acos_global": acos_global,
    }

    print(f"\n{'='*60}")
    print(f"📊 MÉTRICAS FINAIS")
    print(f"{'='*60}")
    print(f"   Anúncios: {len(df)} total | {ativos} ativos | {desativados} desativados | {movidos} movidos")
    print(f"   Impressões:   {total_impressoes:,}")
    print(f"   Cliques:      {total_cliques:,}")
    print(f"   CTR médio:    {ctr_medio:.2f}%")
    print(f"   CPC médio:    R$ {cpc_medio:.2f}")
    print(f"   CVR médio:    {cvr_medio:.2f}%")
    print(f"   Vendas:       {total_vendas} ({total_vendas_dir} diretas + {total_vendas_ind} indiretas)")
    print(f"   Receita:      R$ {total_receita:,.2f}")
    print(f"   Investimento: R$ {total_investimento:,.2f}")
    print(f"   ROAS global:  {roas_global:.2f}x")
    print(f"   ACOS global:  {acos_global:.2f}%")
    print(f"{'='*60}\n")

    # Salva Parquet
    upload_id = str(uuid.uuid4())
    out_dir = os.path.join("data", "anuncios", str(user_id))
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f"{upload_id}.parquet")
    df.to_parquet(out_path, index=False, engine="pyarrow")
    print(f"💾 Parquet salvo: {out_path}\n")

    return {
        "upload_id":    upload_id,
        "rows":         int(len(df)),
        "parquet_path": out_path,
        "metrics":      metrics,
    }