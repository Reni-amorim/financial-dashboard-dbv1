import os
from glob import glob
import pandas as pd
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.database import get_db
from app.models.user import User

router = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard"])

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


def _latest_parquet_for_user(user_id: int, upload_type: str = "faturamento") -> str | None:
    """
    Retorna o arquivo Parquet mais recente do usuário por tipo
    
    Args:
        user_id: ID do usuário
        upload_type: Tipo de upload ("faturamento" ou "anuncios")
    """
    pattern = os.path.join("data", upload_type, str(user_id), "*.parquet")
    files = glob(pattern)
    if not files:
        return None
    files.sort(key=os.path.getmtime, reverse=True)
    return files[0]


@router.get("/")
def get_dashboard(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Retorna dados do dashboard de faturamento
    """
    # Especifica que quer dados de faturamento
    parquet_path = _latest_parquet_for_user(current_user.id, upload_type="faturamento")

    if not parquet_path:
        return {
            "username": current_user.username,
            "transactions": 0,
            "totals": {},
            "summary": {
                "total_creditos": 0.0,
                "total_debitos": 0.0,
                "total_liquido": 0.0,
            },
            "monthly": [],
            "source_file": None,
            "message": "Faça um upload de uma planilha de faturamento para obter o relatório",
        }

    # Lê Parquet (valores já vêm como float)
    df = pd.read_parquet(parquet_path)
    
    print(f"\n{'='*60}")
    print(f"📊 DASHBOARD - Carregando dados")
    print(f"{'='*60}")
    print(f"Arquivo: {os.path.basename(parquet_path)}")
    print(f"Linhas: {len(df)}")

    # Totais por coluna monetária
    totals = {}
    present_cols = [c for c in MONEY_COLS if c in df.columns]
    
    for col in present_cols:
        total = float(df[col].sum())
        totals[col] = total
        print(f"💰 {col}: R$ {total:,.2f}")

    # Calcula resumo financeiro
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
    total_debitos = sum(abs(df[col].sum()) for col in debitos_cols if col in df.columns)
    total_liquido = total_creditos - total_debitos
    
    summary = {
        "total_creditos": float(total_creditos),
        "total_debitos": float(total_debitos),
        "total_liquido": float(total_liquido),
    }
    
    print(f"\n💰 RESUMO FINANCEIRO:")
    print(f"   Créditos: R$ {total_creditos:,.2f}")
    print(f"   Débitos:  R$ {total_debitos:,.2f}")
    print(f"   Líquido:  R$ {total_liquido:,.2f}")

    # Série mensal
    monthly = []
    if "ano_mes" in df.columns and present_cols:
        g = df.groupby("ano_mes")[present_cols].sum().reset_index()
        
        for _, row in g.iterrows():
            record = {"ano_mes": row["ano_mes"]}
            for col in present_cols:
                record[col] = float(row[col])
            
            # Adiciona créditos/débitos mensais
            mes_creditos = sum(row[col] for col in creditos_cols if col in row)
            mes_debitos = sum(abs(row[col]) for col in debitos_cols if col in row)
            
            record["creditos"] = float(mes_creditos)
            record["debitos"] = float(mes_debitos)
            record["liquido"] = float(mes_creditos - mes_debitos)
            
            monthly.append(record)
        
        print(f"\n📅 Dados mensais: {len(monthly)} meses")
    
    print(f"{'='*60}\n")

    return {
        "username": current_user.username,
        "transactions": int(len(df)),
        "totals": totals,
        "summary": summary,
        "monthly": monthly,
        "source_file": os.path.basename(parquet_path),
    }   