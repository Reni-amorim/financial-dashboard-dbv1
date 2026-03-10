"""
Processador de planilha de Anúncios Patrocinados - Mercado Livre
Campos baseados no relatório real: 'Relatório Anúncios patrocinados'
"""
import os
import uuid
import pandas as pd
from typing import Dict


# ─────────────────────────────────────────────
# Configuração da planilha
# ─────────────────────────────────────────────

# Aba que contém os dados
ANUNCIOS_SHEET = "Relatório Anúncios patrocinados"

# Linha que contém o cabeçalho real (0-indexed) — linha 1 no Excel
ANUNCIOS_HEADER_ROW = 1

# Coluna chave usada para localizar o cabeçalho (fallback por busca)
ANUNCIOS_KEY_HEADER = "Título do anúncio patrocinado"

# Valores que indicam "sem dado" nas colunas numéricas
NULL_VALUES = {"-", "", "nan", "None", "NaN", "N/A"}

# Colunas de data
DATE_COLS = ["Desde", "Até"]

# Colunas de texto/categoria
TEXT_COLS = [
    "Campanha",
    "Título do anúncio patrocinado",
    "Código do anúncio",
    "Status",
]

# Colunas numéricas inteiras
INT_COLS = [
    "Impressões",
    "Cliques",
    "Vendas diretas",
    "Vendas indiretas",
    "Vendas por publicidade (Diretas + Indiretas)",
]

# Colunas numéricas float (métricas de performance)
# Nota: CPC vem como "0.33" (ponto decimal, formato US) — tratado por _to_float
FLOAT_COLS = [
    "CPC  (Custo por clique)",
    "CTR (Click Through Rate)",
    "CVR (Conversion rate)",
    "ACOS  (Investimento / Receitas)",
    "ROAS (Receitas / Investimento)",
]

# Colunas monetárias (R$)
MONEY_COLS = [
    "Receita (Moeda local)",
    "Investimento (Moeda local)",
    "Receita por vendas diretas (Moeda Local)",
    "Receita por vendas indiretas",
]

# Todos os campos esperados (para validação)
ALL_EXPECTED_COLS = DATE_COLS + TEXT_COLS + INT_COLS + FLOAT_COLS + MONEY_COLS


# ─────────────────────────────────────────────
# Funções de conversão
# ─────────────────────────────────────────────

def _to_int(series: pd.Series) -> pd.Series:
    """Converte coluna para inteiro. Trata '-' e nulos como 0."""
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
    """Converte coluna para float. Trata '-' e nulos como 0.0."""
    def clean(val):
        if isinstance(val, (int, float)):
            return 0.0 if pd.isna(val) else float(val)
        val = str(val).strip()
        if val in NULL_VALUES:
            return 0.0
        # Formato BR: vírgula decimal
        val = val.replace(",", ".")
        try:
            return float(val)
        except ValueError:
            return 0.0

    return series.apply(clean).astype(float)


def _to_money(series: pd.Series) -> pd.Series:
    """
    Converte coluna monetária para float.
    Suporta formatos: 'R$ 1.234,56', '1234.56', '578.8800048828125', '-', etc.
    """
    def clean(val):
        if isinstance(val, (int, float)):
            return 0.0 if pd.isna(val) else float(val)
        val = str(val).strip()
        if val in NULL_VALUES:
            return 0.0
        # Remove R$ e espaços
        val = val.replace("R$", "").replace("\u00a0", "").replace(" ", "").strip()
        if not val:
            return 0.0
        num_dots = val.count(".")
        num_commas = val.count(",")
        if num_commas > 0 and num_dots > 0:
            # Formato BR: 1.234,56
            val = val.replace(".", "").replace(",", ".")
        elif num_commas > 0 and num_dots == 0:
            # Formato BR sem milhar: 1234,56
            val = val.replace(",", ".")
        # Formato US ou float puro: já está correto
        val = "".join(c for c in val if c.isdigit() or c in ".-")
        try:
            return float(val)
        except ValueError:
            return 0.0

    return series.apply(clean).astype(float)


def _to_date(series: pd.Series) -> pd.Series:
    """
    Converte coluna de data.
    Tenta o formato '06-fev-2026' (português) antes de fazer fallback genérico.
    """
    # Mapeia abreviações PT-BR para EN para o strptime entender
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
    """Normaliza coluna Status. NaN → 'Sem status'."""
    return series.fillna("Sem status").str.strip()


# ─────────────────────────────────────────────
# Leitura e processamento
# ─────────────────────────────────────────────

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


def read_anuncios_table(xlsx_path: str) -> pd.DataFrame:
    """
    Lê a planilha de anúncios patrocinados.
    Tenta usar ANUNCIOS_HEADER_ROW primeiro; se falhar, busca pelo ANUNCIOS_KEY_HEADER.
    """
    # Tentativa direta pelo número da linha
    try:
        df = pd.read_excel(
            xlsx_path,
            sheet_name=ANUNCIOS_SHEET,
            header=ANUNCIOS_HEADER_ROW,
            dtype=str,
        )
        df.columns = [str(c).replace("\u00a0", " ").strip().replace("\n", " ") for c in df.columns]
        df.columns = [" ".join(c.split()) for c in df.columns]
        if ANUNCIOS_KEY_HEADER in df.columns:
            print(f"✅ Cabeçalho encontrado na linha {ANUNCIOS_HEADER_ROW}")
        else:
            raise ValueError("Coluna chave não encontrada — tentando busca por linha")
    except Exception:
        # Fallback: busca linha por linha
        preview = pd.read_excel(xlsx_path, sheet_name=ANUNCIOS_SHEET, header=None, nrows=20, dtype=str)
        header_row = None
        for i in range(len(preview)):
            row = preview.iloc[i].tolist()
            if any(ANUNCIOS_KEY_HEADER in str(cell) for cell in row):
                header_row = i
                break
        if header_row is None:
            raise ValueError(f"Não encontrei cabeçalho com '{ANUNCIOS_KEY_HEADER}'")
        df = pd.read_excel(xlsx_path, sheet_name=ANUNCIOS_SHEET, header=header_row, dtype=str)
        df.columns = [str(c).replace("\u00a0", " ").strip().replace("\n", " ") for c in df.columns]
        df.columns = [" ".join(c.split()) for c in df.columns]
        print(f"✅ Cabeçalho encontrado na linha {header_row} (fallback)")

    # Remove colunas e linhas completamente vazias
    df = df.dropna(axis=1, how="all").dropna(how="all")
    df.columns = _dedupe_columns(list(df.columns))
    return df


def process_anuncios_to_parquet(xlsx_path: str, user_id: int) -> dict:
    """
    Lê, limpa, tipifica e salva em Parquet a planilha de anúncios patrocinados.

    Args:
        xlsx_path: Caminho do arquivo XLSX
        user_id:   ID do usuário

    Returns:
        dict com: upload_id, rows, parquet_path, metrics
    """
    df = read_anuncios_table(xlsx_path)

    print(f"\n{'='*60}")
    print(f"📢 PROCESSANDO PLANILHA DE ANÚNCIOS PATROCINADOS")
    print(f"{'='*60}")
    print(f"📊 Linhas brutas: {len(df)}")

    # ── Datas ──────────────────────────────────────────────
    for col in DATE_COLS:
        if col in df.columns:
            df[col] = _to_date(df[col])
            print(f"   📅 {col}: convertido para datetime")

    # ── Status ─────────────────────────────────────────────
    if "Status" in df.columns:
        df["Status"] = _normalize_status(df["Status"])
        print(f"   🏷️  Status normalizado: {df['Status'].unique().tolist()}")

    # ── Inteiros ───────────────────────────────────────────
    for col in INT_COLS:
        if col in df.columns:
            df[col] = _to_int(df[col])
            print(f"   🔢 {col}: {df[col].sum():,}")

    # ── Floats (métricas %) ────────────────────────────────
    for col in FLOAT_COLS:
        if col in df.columns:
            df[col] = _to_float(df[col])
            print(f"   📈 {col}: média {df[col][df[col] > 0].mean():.2f}")

    # ── Monetários ─────────────────────────────────────────
    for col in MONEY_COLS:
        if col in df.columns:
            df[col] = _to_money(df[col])
            print(f"   💰 {col}: R$ {df[col].sum():,.2f}")

    # ── Coluna auxiliar: campanha_periodo ──────────────────
    if "Campanha" in df.columns and "Desde" in df.columns:
        df["campanha_periodo"] = (
            df["Campanha"].fillna("") + " | " +
            df["Desde"].dt.strftime("%d/%m/%Y").fillna("")
        )

    # ─────────────────────────────────────────────────────
    # Cálculo de métricas para retorno
    # ─────────────────────────────────────────────────────
    ativos       = int((df["Status"] == "Ativo").sum()) if "Status" in df.columns else 0
    desativados  = int((df["Status"] == "Desativada").sum()) if "Status" in df.columns else 0
    movidos      = int((df["Status"] == "Movido").sum()) if "Status" in df.columns else 0
    sem_status   = int((df["Status"] == "Sem status").sum()) if "Status" in df.columns else 0

    total_impressoes  = int(df["Impressões"].sum()) if "Impressões" in df.columns else 0
    total_cliques     = int(df["Cliques"].sum()) if "Cliques" in df.columns else 0
    total_vendas_dir  = int(df["Vendas diretas"].sum()) if "Vendas diretas" in df.columns else 0
    total_vendas_ind  = int(df["Vendas indiretas"].sum()) if "Vendas indiretas" in df.columns else 0
    total_vendas      = int(df["Vendas por publicidade (Diretas + Indiretas)"].sum()) if "Vendas por publicidade (Diretas + Indiretas)" in df.columns else 0

    total_receita     = float(df["Receita (Moeda local)"].sum()) if "Receita (Moeda local)" in df.columns else 0.0
    total_investimento = float(df["Investimento (Moeda local)"].sum()) if "Investimento (Moeda local)" in df.columns else 0.0
    total_receita_dir = float(df["Receita por vendas diretas (Moeda Local)"].sum()) if "Receita por vendas diretas (Moeda Local)" in df.columns else 0.0
    total_receita_ind = float(df["Receita por vendas indiretas"].sum()) if "Receita por vendas indiretas" in df.columns else 0.0

    # CTR, ACOS, ROAS, CPC médios (apenas anúncios com cliques > 0)
    df_ativos = df[df["Cliques"] > 0] if "Cliques" in df.columns else df
    ctr_medio  = float(df_ativos["CTR (Click Through Rate)"].mean())  if "CTR (Click Through Rate)"        in df_ativos.columns and len(df_ativos) > 0 else 0.0
    cvr_medio  = float(df_ativos["CVR (Conversion rate)"].mean())     if "CVR (Conversion rate)"           in df_ativos.columns and len(df_ativos) > 0 else 0.0
    cpc_medio  = float(df_ativos["CPC  (Custo por clique)"].mean())   if "CPC  (Custo por clique)"         in df_ativos.columns and len(df_ativos) > 0 else 0.0
    acos_medio = float(df_ativos["ACOS  (Investimento / Receitas)"].mean()) if "ACOS  (Investimento / Receitas)" in df_ativos.columns and len(df_ativos) > 0 else 0.0
    roas_medio = float(df_ativos["ROAS (Receitas / Investimento)"].mean())  if "ROAS (Receitas / Investimento)"  in df_ativos.columns and len(df_ativos) > 0 else 0.0

    # ROAS e ACOS globais (calculados sobre totais)
    roas_global = round(total_receita / total_investimento, 2) if total_investimento > 0 else 0.0
    acos_global = round((total_investimento / total_receita) * 100, 2) if total_receita > 0 else 0.0

    metrics = {
        # Contagens
        "total_anuncios":    int(len(df)),
        "anuncios_ativos":   ativos,
        "anuncios_desativados": desativados,
        "anuncios_movidos":  movidos,
        "anuncios_sem_status": sem_status,
        # Volume
        "total_impressoes":  total_impressoes,
        "total_cliques":     total_cliques,
        "total_vendas":      total_vendas,
        "total_vendas_diretas":  total_vendas_dir,
        "total_vendas_indiretas": total_vendas_ind,
        # Financeiro
        "total_receita":         total_receita,
        "total_investimento":    total_investimento,
        "total_receita_direta":  total_receita_dir,
        "total_receita_indireta": total_receita_ind,
        # Eficiência (médias sobre anúncios com cliques)
        "ctr_medio":   round(ctr_medio, 4),
        "cvr_medio":   round(cvr_medio, 4),
        "cpc_medio":   round(cpc_medio, 4),
        "acos_medio":  round(acos_medio, 4),
        "roas_medio":  round(roas_medio, 4),
        # Eficiência global
        "roas_global": roas_global,
        "acos_global": acos_global,
    }

    print(f"\n{'='*60}")
    print(f"📊 MÉTRICAS FINAIS")
    print(f"{'='*60}")
    print(f"   Anúncios:      {len(df)} total | {ativos} ativos | {desativados} desativados | {movidos} movidos")
    print(f"   Impressões:    {total_impressoes:,}")
    print(f"   Cliques:       {total_cliques:,}")
    print(f"   CTR médio:     {ctr_medio:.2f}%")
    print(f"   CPC médio:     R$ {cpc_medio:.2f}")
    print(f"   CVR médio:     {cvr_medio:.2f}%")
    print(f"   Vendas totais: {total_vendas} ({total_vendas_dir} diretas + {total_vendas_ind} indiretas)")
    print(f"   Receita:       R$ {total_receita:,.2f}")
    print(f"   Investimento:  R$ {total_investimento:,.2f}")
    print(f"   ROAS global:   {roas_global:.2f}x")
    print(f"   ACOS global:   {acos_global:.2f}%")
    print(f"{'='*60}\n")

    # ── Salva Parquet ──────────────────────────────────────
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