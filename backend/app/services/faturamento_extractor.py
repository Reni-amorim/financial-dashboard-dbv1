"""
Extractor de faturamento — substitui o upload manual de XLSX.

Faz SELECT direto no banco externo `meli` (read-only), aplica o mesmo
cálculo de ICMS por linha usado no pipeline XLSX e salva um Parquet
em `data/faturamento/{user_id}/{account_id}/<uuid>.parquet`.

Os aliases das colunas do SELECT espelham 1:1 os nomes do XLSX antigo,
para reaproveitar `_calcular_icms_linha` e `calcular_metricas` sem
alterações.
"""

import uuid
from pathlib import Path

import pandas as pd
from sqlalchemy import text

from app.db.external_database import get_external_engine
from app.services.financial_calculator import calcular_metricas
from app.services.xlsx_processor import _calcular_icms_linha

SQL = """
SELECT
  o.external_order_id           AS "N.º de venda",
  o.data_criacao                AS "Data da venda",
  o.status                      AS "Estado",
  o.receita_produtos            AS "Receita por produtos (BRL)",
  o.acrescimo_parcelamento      AS "Receita por acréscimo no preço (pago pelo comprador)",
  COALESCE(o.parcelas, 0) * COALESCE(o.valor_parcela, 0)
                                AS "Taxa de parcelamento equivalente ao acréscimo",
  o.tarifa_venda                AS "Tarifa de venda e impostos (BRL)",
  o.receita_envio               AS "Receita por envio (BRL)",
  o.tarifa_envio                AS "Tarifas de envio (BRL)",
  o.custo_envio_declarado       AS "Custo de envio com base nas medidas e peso declarados",
  o.custo_diferenca_peso        AS "Custo por diferenças nas medidas e no peso do pacote",
  o.total_refund                AS "Cancelamentos e reembolsos (BRL)",
  o.valor                       AS "Total (BRL)",
  o.rebate_meli                 AS "rebate_meli",
  s.estado                      AS "Estado.1",
  COALESCE(b.doc_tipo, '') || ' ' || COALESCE(b.doc_numero, '')
                                AS "Tipo e número do documento",
  CASE WHEN b.ie IS NULL OR b.ie = '' THEN 'Não contribuinte'
       ELSE 'Contribuinte' END  AS "Tipo de contribuinte"
FROM orders o
JOIN account  a ON a.id = o.account_id
LEFT JOIN shipping s ON s.order_id = o.id
LEFT JOIN billing  b ON b.order_id = o.id
WHERE a.marketplace_id = :marketplace_id
  AND o.deleted_at IS NULL
  AND a.deleted_at IS NULL;
"""


def extract_and_cache(
    user_id: int,
    account_id: int,
    marketplace_id: int,
    estado_origem: str,
) -> dict:
    """
    Extrai faturamento do banco `meli` para um account, calcula ICMS por
    linha e salva snapshot em Parquet (sobrescrevendo o anterior do mesmo
    account).
    """
    engine = get_external_engine()
    with engine.connect() as conn:
        df = pd.read_sql(text(SQL), conn, params={"marketplace_id": marketplace_id})

    if df.empty:
        raise ValueError(
            f"Nenhum pedido encontrado para marketplace_id={marketplace_id}"
        )

    icms_df = df.apply(lambda r: _calcular_icms_linha(r, estado_origem), axis=1)
    df = pd.concat([df, icms_df], axis=1)

    out_dir = Path("data/faturamento") / str(user_id) / str(account_id)
    out_dir.mkdir(parents=True, exist_ok=True)
    for old in out_dir.glob("*.parquet"):
        old.unlink()
    parquet_path = out_dir / f"{uuid.uuid4()}.parquet"
    df.to_parquet(parquet_path, index=False)

    return {
        "rows": int(len(df)),
        "parquet_path": str(parquet_path),
        "summary": calcular_metricas(df),
        "account_id": account_id,
    }