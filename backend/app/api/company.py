from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.db.database import get_db
from app.models.company import Company
from app.schemas.company import CompanyCreate, CompanyUpdate, CompanyOut
from app.core.deps import get_current_user
from app.models.user import User

router = APIRouter(prefix="/api/v1/company", tags=["company"])


@router.post("/", response_model=CompanyOut, status_code=status.HTTP_201_CREATED)
def criar_company(
    payload: CompanyCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    company = Company(
        user_id=current_user.id,
        name=payload.name,
        document=payload.document,
        state_origin=payload.state_origin.upper(),
        regime_tributario=payload.regime_tributario,
    )
    db.add(company)
    db.commit()
    db.refresh(company)
    return company


@router.get("/", response_model=List[CompanyOut])
def listar_companies(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return (
        db.query(Company)
        .filter(Company.user_id == current_user.id)
        .order_by(Company.created_at.desc())
        .all()
    )


@router.get("/{company_id}", response_model=CompanyOut)
def buscar_company(
    company_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    company = (
        db.query(Company)
        .filter(Company.id == company_id, Company.user_id == current_user.id)
        .first()
    )
    if not company:
        raise HTTPException(status_code=404, detail="Company não encontrada")
    return company


@router.put("/{company_id}", response_model=CompanyOut)
def atualizar_company(
    company_id: int,
    payload: CompanyUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    company = (
        db.query(Company)
        .filter(Company.id == company_id, Company.user_id == current_user.id)
        .first()
    )
    if not company:
        raise HTTPException(status_code=404, detail="Company não encontrada")

    if payload.name:              company.name = payload.name
    if payload.document:          company.document = payload.document
    if payload.state_origin:      company.state_origin = payload.state_origin.upper()
    if payload.regime_tributario: company.regime_tributario = payload.regime_tributario

    db.commit()
    db.refresh(company)
    return company


@router.delete("/{company_id}", status_code=status.HTTP_204_NO_CONTENT)
def deletar_company(
    company_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    company = (
        db.query(Company)
        .filter(Company.id == company_id, Company.user_id == current_user.id)
        .first()
    )
    if not company:
        raise HTTPException(status_code=404, detail="Company não encontrada")

    db.delete(company)
    db.commit()