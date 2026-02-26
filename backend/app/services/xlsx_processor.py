import os
import uuid
import pandas as pd

KEY_HEADER = "N.º de venda"

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


def _to_brl_number(series: pd.Series) -> pd.Series:
    """
    Converte valores monetários para float, suportando formatos BR e US
    
    Formatos suportados:
    - Brasileiro: "R$ 1.234,56" → 1234.56
    - Americano: "1,234.56" → 1234.56
    - Simples: "18.75" → 18.75
    - Simples: "699" → 699.0
    - Negativos: "-118.83" → -118.83
    - Float direto: 18.75 → 18.75
    """
    
    def clean_value(val):
        # Se já é número, retorna como string
        if isinstance(val, (int, float)):
            if pd.isna(val):
                return "0"
            return str(val)
        
        # Converte para string
        val = str(val).strip()
        
        # Trata valores nulos
        if not val or val in ["", "nan", "None", "NaN"]:
            return "0"
        
        # Remove R$ e espaços
        val = val.replace("R$", "").replace("\u00a0", "").replace(" ", "").strip()
        
        if not val:
            return "0"
        
        # Conta pontos e vírgulas
        num_pontos = val.count('.')
        num_virgulas = val.count(',')
        
        # CASO 1: Tem vírgula E ponto → formato BR "1.234,56"
        if num_virgulas > 0 and num_pontos > 0:
            val = val.replace(".", "")  # Remove milhar
            val = val.replace(",", ".")  # Vírgula vira ponto
        
        # CASO 2: Só tem vírgula → formato BR "1234,56"
        elif num_virgulas > 0 and num_pontos == 0:
            val = val.replace(",", ".")
        
        # CASO 3: Só tem ponto → formato US "18.75" ou "1.234"
        elif num_pontos > 0 and num_virgulas == 0:
            # Se tem mais de um ponto → formato com milhares "1.234.567"
            if num_pontos > 1:
                parts = val.split('.')
                val = ''.join(parts[:-1]) + '.' + parts[-1]
            # Um ponto apenas → já está correto (decimal)
        
        # CASO 4: Não tem separador → valor inteiro "699"
        # Não faz nada, já está correto
        
        # Remove caracteres não numéricos exceto ponto e menos
        val = ''.join(c for c in val if c.isdigit() or c in '.-')
        
        return val if val else "0"
    
    # Aplica limpeza
    cleaned = series.apply(clean_value)
    
    # Converte para numérico
    result = pd.to_numeric(cleaned, errors="coerce").fillna(0.0)
    
    return result

def find_header_row(xlsx_path: str) -> int:
    """Encontra a linha que contém o cabeçalho"""
    preview = pd.read_excel(xlsx_path, header=None, nrows=120, dtype=str)

    for i in range(len(preview)):
        row = preview.iloc[i].tolist()
        if any(KEY_HEADER in str(cell) for cell in row):
            return i

    raise ValueError("Não encontrei a linha de cabeçalho com 'N.º de venda'.")


def read_data_table(xlsx_path: str) -> pd.DataFrame:
    """
    Lê o XLSX usando a linha correta como header, removendo colunas vazias
    e normalizando nomes.
    """
    header_row = find_header_row(xlsx_path)
    df = pd.read_excel(xlsx_path, header=header_row, dtype=str)

    # Remove colunas totalmente vazias
    df = df.dropna(axis=1, how="all")

    # Normaliza nomes (remove espaços invisíveis)
    df.columns = [str(c).replace("\u00a0", " ").strip() for c in df.columns]
    df.columns = [" ".join(c.split()) for c in df.columns]

    # Dedup (caso tenha colunas repetidas)
    df.columns = _dedupe_columns(list(df.columns))
    
    # Remove linhas completamente vazias
    df = df.dropna(how="all")

    return df


def process_xlsx_to_parquet(xlsx_path: str, user_id: int) -> dict:
    """
    Processa arquivo XLSX e salva em Parquet

    Args:
        xlsx_path: Caminho do arquivo XLSX
        user_id: ID do usuário

    Returns:
        Dicionário com informações do processamento
    """
    df = read_data_table(xlsx_path)
    
    print(f"\n{'='*60}")
    print(f"🔍 PROCESSANDO ARQUIVO")
    print(f"{'='*60}")
    print(f"📊 Total de linhas: {len(df)}")

    # Processa datas
    if "Data da venda" in df.columns:
        df["Data da venda"] = pd.to_datetime(
            df["Data da venda"], errors="coerce", dayfirst=True
        )
        df["ano_mes"] = df["Data da venda"].dt.to_period("M").astype(str)
    else:
        df["ano_mes"] = "desconhecido"

    # Converte colunas monetárias para float
    present_money_cols = []
    
    for col in MONEY_COLS:
        if col in df.columns:
            print(f"\n💰 Processando: {col}")
            
            # Debug: valores ANTES da conversão
            samples = df[col].head(3).tolist()
            print(f"   Antes: {samples}")
            
            # Converte
            df[col] = _to_brl_number(df[col])
            
            # Debug: valores DEPOIS da conversão
            samples_after = df[col].head(3).tolist()
            print(f"   Depois: {samples_after}")
            
            # Estatísticas
            col_sum = df[col].sum()
            print(f"   Soma: R$ {col_sum:,.2f}")
            print(f"   Min: R$ {df[col].min():,.2f}")
            print(f"   Max: R$ {df[col].max():,.2f}")
            
            present_money_cols.append(col)

    # 🔥 NOVO: Calcula créditos e débitos
    creditos_cols = [
        "Receita por produtos (BRL)",
        "Receita por acréscimo no preço (pago pelo comprador)",
        "Receita por envio (BRL)",
    ]
    
    debitos_cols = [
        "Taxa de parcelamento equivalente ao acréscimo",
        "Tarifa de venda e impostos (BRL)",
        "Custo de envio com base nas medidas e peso declarados",
        "Custo por diferenças nas medidas e no peso do pacote",
        "Cancelamentos e reembolsos (BRL)",
    ]
    
    # Calcula totais
    total_creditos = 0.0
    total_debitos = 0.0
    
    for col in creditos_cols:
        if col in df.columns:
            total_creditos += df[col].sum()
    
    for col in debitos_cols:
        if col in df.columns:
            # Valores negativos somam como débito
            total_debitos += abs(df[col].sum())
    
    total_liquido = total_creditos - total_debitos

    # Calcula totais individuais por coluna
    totals = {}
    
    print(f"\n{'='*60}")
    print(f"✅ TOTAIS POR COLUNA")
    print(f"{'='*60}")
    
    for col in present_money_cols:
        total = float(df[col].sum())
        totals[col] = total
        print(f"   {col}: R$ {total:,.2f}")
    
    # 🔥 NOVO: Adiciona resumo de créditos/débitos
    print(f"\n{'='*60}")
    print(f"💰 RESUMO FINANCEIRO")
    print(f"{'='*60}")
    print(f"   ✅ Total Créditos:  R$ {total_creditos:,.2f}")
    print(f"   ❌ Total Débitos:   R$ {total_debitos:,.2f}")
    print(f"   💵 Líquido:         R$ {total_liquido:,.2f}")
    print(f"{'='*60}\n")

    # Salva Parquet
    upload_id = str(uuid.uuid4())
    out_dir = os.path.join("data", "processed", str(user_id))
    os.makedirs(out_dir, exist_ok=True)

    out_path = os.path.join(out_dir, f"{upload_id}.parquet")
    df.to_parquet(out_path, index=False, engine='pyarrow')
    
    print(f"💾 Parquet salvo: {out_path}\n")

    return {
        "upload_id": upload_id,
        "rows": int(len(df)),
        "parquet_path": out_path,
        "totals": totals,
        # 🔥 NOVO: Adiciona resumo financeiro
        "summary": {
            "total_creditos": float(total_creditos),
            "total_debitos": float(total_debitos),
            "total_liquido": float(total_liquido),
        }
    }