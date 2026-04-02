import os
import uuid
import pandas as pd

from app.services.icms_calculator import calcular_icms

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

# Colunas extras necessárias para o cálculo de ICMS
ICMS_COLS = [
    "Estado.1",                                              # estado destino do comprador
    "Tipo e número do documento",                            # CPF ou CNPJ
    "Tipo de contribuinte",                                  # Contribuinte / Não contribuinte
]

_MESES_PT = {
    "janeiro": "01", "fevereiro": "02", "março": "03", "abril": "04",
    "maio": "05", "junho": "06", "julho": "07", "agosto": "08",
    "setembro": "09", "outubro": "10", "novembro": "11", "dezembro": "12",
}


def _parse_data_pt(val) -> "pd.Timestamp":
    """Converte 'DD de mês de YYYY HH:MM hs.' para Timestamp."""
    if pd.isna(val) or not isinstance(val, str):
        return pd.NaT
    v = val.strip().lower().replace(" hs.", "").replace("hs.", "").strip()
    for mes_nome, mes_num in _MESES_PT.items():
        if mes_nome in v:
            v = v.replace(f" de {mes_nome} de ", f"/{mes_num}/")
            v = v.replace(f" de {mes_nome} ",    f"/{mes_num}/")
            break
    for fmt in ["%d/%m/%Y %H:%M", "%d/%m/%Y"]:
        try:
            return pd.to_datetime(v, format=fmt)
        except Exception:
            pass
    return pd.NaT


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
        if isinstance(val, (int, float)):
            if pd.isna(val):
                return "0"
            return str(val)

        val = str(val).strip()

        if not val or val in ["", "nan", "None", "NaN"]:
            return "0"

        val = val.replace("R$", "").replace("\u00a0", "").replace(" ", "").strip()

        if not val:
            return "0"

        num_pontos  = val.count('.')
        num_virgulas = val.count(',')

        if num_virgulas > 0 and num_pontos > 0:
            val = val.replace(".", "")
            val = val.replace(",", ".")
        elif num_virgulas > 0 and num_pontos == 0:
            val = val.replace(",", ".")
        elif num_pontos > 0 and num_virgulas == 0:
            if num_pontos > 1:
                parts = val.split('.')
                val = ''.join(parts[:-1]) + '.' + parts[-1]

        val = ''.join(c for c in val if c.isdigit() or c in '.-')

        return val if val else "0"

    cleaned = series.apply(clean_value)
    result  = pd.to_numeric(cleaned, errors="coerce").fillna(0.0)

    return result


def _calcular_icms_linha(row: pd.Series, estado_origem: str) -> pd.Series:
    """
    Calcula o ICMS para uma linha da planilha.
    Retorna uma Series com as colunas de ICMS.
    """
    try:
        receita   = float(row.get("Receita por produtos (BRL)", 0) or 0)
        acrescimo = float(row.get("Receita por acréscimo no preço (pago pelo comprador)", 0) or 0)
        estado_destino   = str(row.get("Estado.1", "") or "")
        tipo_documento   = str(row.get("Tipo e número do documento", "") or "")
        tipo_contribuinte = str(row.get("Tipo de contribuinte", "") or "")

        if not estado_destino or estado_destino in ["nan", "None", ""]:
            return pd.Series({
                "icms_base_calculo": 0.0,
                "icms_aliquota":     0,
                "icms_valor":        0.0,
                "icms_difal":        0.0,
                "icms_total_venda":        0.0,
                "icms_tipo_pessoa":  "",
                "icms_uf_destino":   "",
            })

        resultado = calcular_icms(
            receita_produto=receita,
            acrescimo=acrescimo,
            estado_origem=estado_origem,
            estado_destino=estado_destino,
            tipo_documento=tipo_documento,
            tipo_contribuinte=tipo_contribuinte,
        )

        return pd.Series({
            "icms_base_calculo": resultado["base_calculo"],
            "icms_aliquota":     resultado["aliquota"],
            "icms_valor":        resultado["icms"],
            "icms_difal":        resultado["difal"],
            "icms_total_venda":        resultado["icms_total_venda"],
            "icms_tipo_pessoa":  resultado["tipo_pessoa"],
            "icms_uf_destino":   resultado["uf_destino"],
        })

    except Exception as e:
        print(f"⚠️ Erro ao calcular ICMS na linha: {e}")
        return pd.Series({
            "icms_base_calculo": 0.0,
            "icms_aliquota":     0,
            "icms_valor":        0.0,
            "icms_difal":        0.0,
            "icms_total_venda":        0.0,
            "icms_tipo_pessoa":  "",
            "icms_uf_destino":   "",
        })


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

    df = df.dropna(axis=1, how="all")

    df.columns = [str(c).replace("\u00a0", " ").strip() for c in df.columns]
    df.columns = [" ".join(c.split()) for c in df.columns]
    df.columns = _dedupe_columns(list(df.columns))

    df = df.dropna(how="all")

    return df


def process_xlsx_to_parquet(xlsx_path: str, user_id: int, estado_origem: str = "SP") -> dict:
    """
    Processa arquivo XLSX e salva em Parquet com colunas de ICMS.

    Args:
        xlsx_path:      Caminho do arquivo XLSX
        user_id:        ID do usuário
        estado_origem:  UF da empresa (buscado do cadastro da empresa)

    Returns:
        Dicionário com informações do processamento incluindo métricas de ICMS
    """
    df = read_data_table(xlsx_path)

    print(f"\n{'='*60}")
    print(f"🔍 PROCESSANDO ARQUIVO")
    print(f"{'='*60}")
    print(f"📊 Total de linhas: {len(df)}")
    print(f"🏢 Estado origem: {estado_origem}")

    # Processa datas
    if "Data da venda" in df.columns:
        df["Data da venda"] = df["Data da venda"].apply(_parse_data_pt)
        df["ano_mes"] = df["Data da venda"].dt.to_period("M").astype(str)
    else:
        df["ano_mes"] = "desconhecido"

    # Converte colunas monetárias para float
    present_money_cols = []

    for col in MONEY_COLS:
        if col in df.columns:
            print(f"\n💰 Processando: {col}")

            samples = df[col].head(3).tolist()
            print(f"   Antes: {samples}")

            df[col] = _to_brl_number(df[col])

            samples_after = df[col].head(3).tolist()
            print(f"   Depois: {samples_after}")

            col_sum = df[col].sum()
            print(f"   Soma: R$ {col_sum:,.2f}")

            present_money_cols.append(col)

    # Calcula créditos e débitos
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

    total_creditos = sum(df[col].sum() for col in creditos_cols if col in df.columns)
    total_debitos  = sum(abs(df[col].sum()) for col in debitos_cols if col in df.columns)
    total_liquido  = total_creditos - total_debitos

    # ─────────────────────────────────────────────────────────
    # CÁLCULO DE ICMS POR LINHA
    # ─────────────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print(f"🧮 CALCULANDO ICMS POR VENDA")
    print(f"{'='*60}")

    icms_cols = df.apply(
        lambda row: _calcular_icms_linha(row, estado_origem),
        axis=1
    )
    df = pd.concat([df, icms_cols], axis=1)

    # Totais de ICMS
    total_icms       = round(float(df["icms_valor"].sum()), 2)
    total_difal      = round(float(df["icms_difal"].sum()), 2)
    total_icms_total = round(float(df["icms_total_venda"].sum()), 2)

    print(f"   💰 ICMS total:       R$ {total_icms:,.2f}")
    print(f"   💰 DIFAL total:      R$ {total_difal:,.2f}")
    print(f"   💰 ICMS + DIFAL:     R$ {total_icms_total:,.2f}")
    print(f"{'='*60}\n")

    # Totais por coluna
    totals = {col: float(df[col].sum()) for col in present_money_cols}

    print(f"\n{'='*60}")
    print(f"💰 RESUMO FINANCEIRO")
    print(f"{'='*60}")
    print(f"   ✅ Total Créditos:  R$ {total_creditos:,.2f}")
    print(f"   ❌ Total Débitos:   R$ {total_debitos:,.2f}")
    print(f"   💵 Líquido:         R$ {total_liquido:,.2f}")
    print(f"   🧾 ICMS Total:      R$ {total_icms_total:,.2f}")
    print(f"{'='*60}\n")

    # Salva Parquet
    upload_id = str(uuid.uuid4())
    out_dir   = os.path.join("data", "faturamento", str(user_id))
    os.makedirs(out_dir, exist_ok=True)

    out_path = os.path.join(out_dir, f"{upload_id}.parquet")
    df.to_parquet(out_path, index=False, engine='pyarrow')

    print(f"💾 Parquet salvo: {out_path}\n")

    return {
        "upload_id":    upload_id,
        "rows":         int(len(df)),
        "parquet_path": out_path,
        "totals":       totals,
        "summary": {
            "total_creditos":    float(total_creditos),
            "total_debitos":     float(total_debitos),
            "total_liquido":     float(total_liquido),
            "total_icms":        total_icms,
            "total_difal":       total_difal,
            "total_icms_total":  total_icms_total,
        },
    }