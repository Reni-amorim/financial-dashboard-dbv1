"""
Processador de planilha de anúncios
"""
import os
import uuid
import pandas as pd
from typing import Dict


# 🔥 Defina as colunas esperadas da planilha de anúncios
# ⚠️ AJUSTE CONFORME SEU ARQUIVO REAL
ANUNCIOS_KEY_HEADER = "ID do anúncio"  # Coluna chave para identificar o cabeçalho

ANUNCIOS_COLS = [
    "ID do anúncio",
    "Título",
    "Status",
    "Estoque disponível",
    "Preço",
    "Visitas",
    "Vendas",
    "Taxa de conversão",
    "Categoria",
]


def _dedupe_columns(cols: list[str]) -> list[str]:
    """Remove colunas duplicadas adicionando sufixo"""
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


def _to_number(series: pd.Series) -> pd.Series:
    """Converte valores numéricos (visitas, vendas, estoque)"""
    def clean_value(val):
        if isinstance(val, (int, float)):
            if pd.isna(val):
                return "0"
            return str(val)
        
        val = str(val).strip()
        
        if not val or val in ["", "nan", "None", "NaN"]:
            return "0"
        
        # Remove pontos e vírgulas
        val = val.replace(".", "").replace(",", "")
        
        # Remove caracteres não numéricos
        val = ''.join(c for c in val if c.isdigit() or c == '-')
        
        return val if val else "0"
    
    cleaned = series.apply(clean_value)
    return pd.to_numeric(cleaned, errors="coerce").fillna(0.0)


def _to_price(series: pd.Series) -> pd.Series:
    """Converte preços (mesma lógica do faturamento)"""
    from app.services.xlsx_processor import _to_brl_number
    return _to_brl_number(series)


def _to_percentage(series: pd.Series) -> pd.Series:
    """Converte percentuais como '5%' ou '5.5%' para float"""
    def clean_percent(val):
        if isinstance(val, (int, float)):
            if pd.isna(val):
                return "0"
            return str(val)
        
        val = str(val).strip()
        
        if not val or val in ["", "nan", "None", "NaN"]:
            return "0"
        
        # Remove %
        val = val.replace("%", "").strip()
        
        # Converte vírgula para ponto
        val = val.replace(",", ".")
        
        return val if val else "0"
    
    cleaned = series.apply(clean_percent)
    return pd.to_numeric(cleaned, errors="coerce").fillna(0.0)


def find_header_row(xlsx_path: str) -> int:
    """Encontra a linha que contém o cabeçalho"""
    preview = pd.read_excel(xlsx_path, header=None, nrows=120, dtype=str)

    for i in range(len(preview)):
        row = preview.iloc[i].tolist()
        if any(ANUNCIOS_KEY_HEADER in str(cell) for cell in row):
            return i

    raise ValueError(f"Não encontrei a linha de cabeçalho com '{ANUNCIOS_KEY_HEADER}'.")


def read_anuncios_table(xlsx_path: str) -> pd.DataFrame:
    """Lê a planilha de anúncios"""
    header_row = find_header_row(xlsx_path)
    df = pd.read_excel(xlsx_path, header=header_row, dtype=str)

    # Remove colunas vazias
    df = df.dropna(axis=1, how="all")

    # Normaliza nomes
    df.columns = [str(c).replace("\u00a0", " ").strip() for c in df.columns]
    df.columns = [" ".join(c.split()) for c in df.columns]
    df.columns = _dedupe_columns(list(df.columns))
    
    # Remove linhas vazias
    df = df.dropna(how="all")

    return df


def process_anuncios_to_parquet(xlsx_path: str, user_id: int) -> dict:
    """
    Processa planilha de anúncios e salva em Parquet
    
    Args:
        xlsx_path: Caminho do arquivo XLSX
        user_id: ID do usuário
    
    Returns:
        Dicionário com informações do processamento
    """
    df = read_anuncios_table(xlsx_path)
    
    print(f"\n{'='*60}")
    print(f"📢 PROCESSANDO PLANILHA DE ANÚNCIOS")
    print(f"{'='*60}")
    print(f"📊 Total de anúncios: {len(df)}")

    # Processa colunas numéricas
    numeric_cols = ["Estoque disponível", "Visitas", "Vendas"]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = _to_number(df[col])
            print(f"   ✅ {col}: Convertido")

    # Processa preços
    if "Preço" in df.columns:
        df["Preço"] = _to_price(df["Preço"])
        print(f"   ✅ Preço: Convertido")

    # Processa percentuais
    if "Taxa de conversão" in df.columns:
        df["Taxa de conversão"] = _to_percentage(df["Taxa de conversão"])
        print(f"   ✅ Taxa de conversão: Convertido")

    # Calcula métricas
    total_anuncios = len(df)
    anuncios_ativos = len(df[df["Status"] == "Ativo"]) if "Status" in df.columns else 0
    total_visitas = int(df["Visitas"].sum()) if "Visitas" in df.columns else 0
    total_vendas = int(df["Vendas"].sum()) if "Vendas" in df.columns else 0
    taxa_conversao_media = float(df["Taxa de conversão"].mean()) if "Taxa de conversão" in df.columns else 0.0
    
    metrics = {
        "total_anuncios": int(total_anuncios),
        "anuncios_ativos": int(anuncios_ativos),
        "total_visitas": int(total_visitas),
        "total_vendas": int(total_vendas),
        "taxa_conversao_media": float(taxa_conversao_media),
    }
    
    print(f"\n{'='*60}")
    print(f"📊 MÉTRICAS DE ANÚNCIOS")
    print(f"{'='*60}")
    print(f"   Total: {total_anuncios}")
    print(f"   Ativos: {anuncios_ativos}")
    print(f"   Visitas: {total_visitas:,}")
    print(f"   Vendas: {total_vendas:,}")
    print(f"   Taxa conversão média: {taxa_conversao_media:.2f}%")
    print(f"{'='*60}\n")

    # Salva Parquet
    upload_id = str(uuid.uuid4())
    out_dir = os.path.join("data", "anuncios", str(user_id))
    os.makedirs(out_dir, exist_ok=True)

    out_path = os.path.join(out_dir, f"{upload_id}.parquet")
    df.to_parquet(out_path, index=False, engine='pyarrow')
    
    print(f"💾 Parquet salvo: {out_path}\n")

    return {
        "upload_id": upload_id,
        "rows": int(len(df)),
        "parquet_path": out_path,
        "metrics": metrics,
    }