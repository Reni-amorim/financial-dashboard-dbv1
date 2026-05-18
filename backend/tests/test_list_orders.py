"""
Script de inspeção: lista todas as orders do banco externo `meli` para um
dado marketplace_id, usando exatamente o mesmo SELECT do extractor de
faturamento. Ao final, imprime os totais (soma) de cada coluna numérica.

Uso (dentro do container backend):

    docker compose -f docker-compose.prod.yml exec backend \\
        python tests/test_list_orders.py 3243351162
    docker compose -f docker-compose.prod.yml exec backend \\
        python tests/test_list_orders.py 3243351162 --limit 20
    docker compose -f docker-compose.prod.yml exec backend \\
        python tests/test_list_orders.py 3243351162 --csv /app/data/orders.csv
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
from sqlalchemy import text

from app.db.external_database import get_external_engine
from app.services.faturamento_extractor import SQL


def fmt_brl(x: float) -> str:
    return f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def main():
    parser = argparse.ArgumentParser(description="Lista orders do banco meli por marketplace_id e mostra totais.")
    parser.add_argument("marketplace_id", type=int, help="Seller ID do Mercado Livre (bigint).")
    parser.add_argument("--limit", type=int, default=None, help="Limita a N linhas no print da tabela.")
    parser.add_argument("--csv", type=str, default=None, help="Salva o resultado completo em CSV.")
    parser.add_argument("--cols", type=str, default=None,
                        help="Colunas a exibir, separadas por vírgula. Default: todas.")
    args = parser.parse_args()

    engine = get_external_engine()
    sql = SQL
    if args.limit is not None:
        sql_to_run = sql.rstrip().rstrip(";") + f"\nLIMIT {int(args.limit)};"
    else:
        sql_to_run = sql

    with engine.connect() as conn:
        df = pd.read_sql(text(sql_to_run), conn, params={"marketplace_id": args.marketplace_id})

    if df.empty:
        print(f"⚠️  Nenhum pedido encontrado para marketplace_id={args.marketplace_id}")
        sys.exit(1)

    df_view = df
    if args.cols:
        wanted = [c.strip() for c in args.cols.split(",")]
        df_view = df[[c for c in wanted if c in df.columns]]

    print(f"\n{'='*80}")
    print(f"📦 Orders para marketplace_id={args.marketplace_id}")
    print(f"   Total de linhas: {len(df)}")
    print(f"{'='*80}\n")

    pd.set_option("display.max_columns", None)
    pd.set_option("display.width", 200)
    pd.set_option("display.max_colwidth", 40)

    print(df_view.to_string(index=False))

    # ─────────────────────────────────────────────────────────────
    # TOTAIS (soma de todas as colunas numéricas)
    # ─────────────────────────────────────────────────────────────
    numeric_df = df.select_dtypes(include="number")
    if numeric_df.empty:
        print("\n(Nenhuma coluna numérica para somar.)")
    else:
        sums = numeric_df.sum(numeric_only=True)

        print(f"\n{'='*80}")
        print(f"💰 TOTAIS — soma das colunas numéricas ({len(df)} linhas)")
        print(f"{'='*80}")
        name_width = max(len(c) for c in sums.index) + 2
        for col, val in sums.items():
            print(f"  {col:<{name_width}} {fmt_brl(float(val)):>20}")
        print(f"{'='*80}\n")

    print("Colunas disponíveis:")
    for c in df.columns:
        dtype = str(df[c].dtype)
        print(f"  - {c:<55} [{dtype}]")
    print()

    if args.csv:
        df.to_csv(args.csv, index=False, encoding="utf-8-sig")
        print(f"💾 Salvo em: {args.csv}")


if __name__ == "__main__":
    main()