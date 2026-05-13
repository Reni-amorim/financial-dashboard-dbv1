from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.orm import Session
from typing import List, Optional

from app.db.database import get_db
from app.models.account import Account
from app.models.business import Business
from app.models.company import Company
from app.schemas.account import AccountCreate, AccountUpdate, AccountOut
from app.core.deps import get_current_user
from app.models.user import User

router = APIRouter(prefix="/api/v1/account", tags=["account"])


def _get_user_company(db: Session, user_id: int) -> Company:
    company = (
        db.query(Company)
        .filter(Company.admin_user_id == user_id)
        .first()
    )
    if not company:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Usuário não possui company cadastrada.",
        )
    return company


def _validate_business_ownership(db: Session, business_id: int, company_id: int) -> Business:
    business = (
        db.query(Business)
        .filter(
            Business.id == business_id,
            Business.company_id == company_id,
            Business.deleted_at.is_(None),
        )
        .first()
    )
    if not business:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Business inválido ou não pertence à sua company.",
        )
    return business


@router.post("/", response_model=AccountOut, status_code=status.HTTP_201_CREATED)
def criar_account(
    payload: AccountCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas usuários com role 'admin' podem criar um account.",
        )
    company = _get_user_company(db, current_user.id)
    _validate_business_ownership(db, payload.business_id, company.id)

    account = Account(
        business_id=payload.business_id,
        name=payload.name,
        marketplace_id=payload.marketplace_id,
        status=payload.status or "active",
    )
    db.add(account)
    db.commit()
    db.refresh(account)
    return account


@router.get("/", response_model=List[AccountOut])
def listar_accounts(
    business_id: Optional[int] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    company = _get_user_company(db, current_user.id)
    q = (
        db.query(Account)
        .join(Business, Business.id == Account.business_id)
        .filter(
            Business.company_id == company.id,
            Business.deleted_at.is_(None),
            Account.deleted_at.is_(None),
        )
    )
    if business_id is not None:
        q = q.filter(Account.business_id == business_id)
    return q.order_by(Account.created_at.desc()).all()


@router.get("/{account_id}", response_model=AccountOut)
def buscar_account(
    account_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    company = _get_user_company(db, current_user.id)
    account = (
        db.query(Account)
        .join(Business, Business.id == Account.business_id)
        .filter(
            Account.id == account_id,
            Business.company_id == company.id,
            Business.deleted_at.is_(None),
            Account.deleted_at.is_(None),
        )
        .first()
    )
    if not account:
        raise HTTPException(status_code=404, detail="Account não encontrado")
    return account


@router.put("/{account_id}", response_model=AccountOut)
def atualizar_account(
    account_id: int,
    payload: AccountUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas usuários com role 'admin' podem editar um account.",
        )
    company = _get_user_company(db, current_user.id)
    account = (
        db.query(Account)
        .join(Business, Business.id == Account.business_id)
        .filter(
            Account.id == account_id,
            Business.company_id == company.id,
            Business.deleted_at.is_(None),
            Account.deleted_at.is_(None),
        )
        .first()
    )
    if not account:
        raise HTTPException(status_code=404, detail="Account não encontrado")

    if payload.name is not None:           account.name = payload.name
    if payload.marketplace_id is not None: account.marketplace_id = payload.marketplace_id
    if payload.status is not None:         account.status = payload.status

    db.commit()
    db.refresh(account)
    return account


@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
def deletar_account(
    account_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas usuários com role 'admin' podem excluir um account.",
        )
    company = _get_user_company(db, current_user.id)
    account = (
        db.query(Account)
        .join(Business, Business.id == Account.business_id)
        .filter(
            Account.id == account_id,
            Business.company_id == company.id,
            Business.deleted_at.is_(None),
            Account.deleted_at.is_(None),
        )
        .first()
    )
    if not account:
        raise HTTPException(status_code=404, detail="Account não encontrado")

    account.deleted_at = func.now()
    db.commit()