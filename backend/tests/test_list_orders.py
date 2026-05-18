"""
Script de inspeção: lista todas as orders do banco externo `meli` para um
dado marketplace_id, usando exatamente o mesmo SELECT do extractor de
faturamento.

Uso (dentro do container backend):

    docker compose exec backend python tests/list_orders.py 123456789
    docker compose exec backend python tests/list_orders.py 123456789 --limit 20
    docker compose exec backend python tests/list_orders.py 123456789 --csv out.csv

No prod (com network do meli):

    docker compose -f docker-compose.prod.yml exec backend \\
        python tests/list_orders.py 123456789
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
from sqlalchemy import text

from app.db.external_database import get_external_engine
from app.services.faturamento_extractor import SQL


def main():
    parser = argparse.ArgumentParser(description="Lista orders do banco meli por marketplace_id.")
    parser.add_argument("marketplace_id", type=int, help="Seller ID do Mercado Livre (bigint).")
    parser.add_argument("--limit", type=int, default=None, help="Limita a N linhas.")
    parser.add_argument("--csv", type=str, default=None, help="Salva resultado em CSV.")
    parser.add_argument("--cols", type=str, default=None,
                        help="Colunas a exibir, separadas por vírgula. Default: todas.")
    args = parser.parse_args()

    engine = get_external_engine()
    sql = SQL
    if args.limit is not None:
        sql = sql.rstrip().rstrip(";") + f"\nLIMIT {int(args.limit)};"

    with engine.connect() as conn:
        df = pd.read_sql(text(sql), conn, params={"marketplace_id": args.marketplace_id})

    if df.empty:
        print(f"⚠️  Nenhum pedido encontrado para marketplace_id={args.marketplace_id}")
        sys.exit(1)

    if args.cols:
        cols = [c.strip() for c in args.cols.split(",")]
        df = df[[c for c in cols if c in df.columns]]

    print(f"\n{'='*80}")
    print(f"📦 Orders para marketplace_id={args.marketplace_id}")
    print(f"   Total: {len(df)} linha(s)")
    print(f"{'='*80}\n")

    pd.set_option("display.max_columns", None)
    pd.set_option("display.width", 200)
    pd.set_option("display.max_colwidth", 40)

    print(df.to_string(index=False))

    print(f"\n{'='*80}")
    print("Colunas disponíveis:")
    for c in df.columns:
        print(f"  - {c}")
    print(f"{'='*80}\n")

    if args.csv:
        df.to_csv(args.csv, index=False, encoding="utf-8-sig")
        print(f"💾 Salvo em: {args.csv}")


if __name__ == "__main__":
    main()