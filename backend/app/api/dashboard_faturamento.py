import os
from glob import glob
import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.database import get_db
from app.models.user import User
from app.models.company import Company
from app.models.business import Business
from app.models.account import Account
from app.services.financial_calculator import calcular_metricas
from app.services.faturamento_extractor import extract_and_cache

router = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard"])


def _user_accounts(db: Session, user_id: int) -> list[Account]:
    return (
        db.query(Account)
        .join(Business, Business.id == Account.business_id)
        .join(Company, Company.id == Business.company_id)
        .filter(
            Company.admin_user_id == user_id,
            Account.deleted_at.is_(None),
            Business.deleted_at.is_(None),
            Company.deleted_at.is_(None),
        )
        .all()
    )


def _serialize_account(a: Account) -> dict:
    return {
        "id": a.id,
        "name": a.name,
        "marketplace_id": a.marketplace_id,
        "business_id": a.business_id,
    }


def _latest_parquet_for_account(user_id: int, account_id: int) -> str | None:
    pattern = os.path.join("data", "faturamento", str(user_id), str(account_id), "*.parquet")
    files = glob(pattern)
    if not files:
        return None
    files.sort(key=os.path.getmtime, reverse=True)
    return files[0]


@router.get("/accounts")
def list_user_accounts(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return [_serialize_account(a) for a in _user_accounts(db, current_user.id)]


@router.post("/atualizar")
def atualizar_faturamento(
    account_id: int = Query(..., description="ID do Account a atualizar"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    accounts = _user_accounts(db, current_user.id)
    account = next((a for a in accounts if a.id == account_id), None)
    if not account or not account.marketplace_id:
        raise HTTPException(status_code=400, detail="Account inválido ou sem marketplace_id.")

    company = (
        db.query(Company)
        .join(Business, Business.company_id == Company.id)
        .filter(Business.id == account.business_id)
        .first()
    )
    if not company or not company.state_origin:
        raise HTTPException(status_code=400, detail="Cadastre uma company com state_origin.")

    try:
        return extract_and_cache(
            user_id=current_user.id,
            account_id=account.id,
            marketplace_id=account.marketplace_id,
            estado_origem=company.state_origin,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/")
def get_dashboard(
    account_id: int | None = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    accounts = _user_accounts(db, current_user.id)
    accounts_payload = [_serialize_account(a) for a in accounts]

    if account_id is None:
        return {
            "username": current_user.username,
            "accounts": accounts_payload,
            "message": "Selecione um account",
        }

    account = next((a for a in accounts if a.id == account_id), None)
    if not account:
        raise HTTPException(status_code=403, detail="Account não pertence ao usuário.")

    parquet_path = _latest_parquet_for_account(current_user.id, account_id)
    if not parquet_path:
        return {
            "username": current_user.username,
            "accounts": accounts_payload,
            "account_id": account_id,
            "transactions": 0,
            "metricas": {},
            "source_file": None,
            "message": "Clique em Atualizar Dados",
        }

    df = pd.read_parquet(parquet_path)
    metricas = calcular_metricas(df)

    return {
        "username": current_user.username,
        "accounts": accounts_payload,
        "account_id": account_id,
        "transactions": int(len(df)),
        "metricas": metricas,
        "source_file": os.path.basename(parquet_path),
    }