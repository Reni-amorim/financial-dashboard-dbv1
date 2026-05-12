from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session
from typing import List

from app.db.database import get_db
from app.models.business import Business
from app.models.company import Company
from app.schemas.business import BusinessCreate, BusinessUpdate, BusinessOut
from app.core.deps import get_current_user
from app.models.user import User

router = APIRouter(prefix="/api/v1/business", tags=["business"])


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


@router.post("/", response_model=BusinessOut, status_code=status.HTTP_201_CREATED)
def criar_business(
    payload: BusinessCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas usuários com role 'admin' podem criar um business.",
        )
    company = _get_user_company(db, current_user.id)
    business = Business(
        company_id=company.id,
        name=payload.name,
        document=payload.document,
    )
    db.add(business)
    db.commit()
    db.refresh(business)
    return business


@router.get("/", response_model=List[BusinessOut])
def listar_businesses(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    company = _get_user_company(db, current_user.id)
    return (
        db.query(Business)
        .filter(
            Business.company_id == company.id,
            Business.deleted_at.is_(None),
        )
        .order_by(Business.created_at.desc())
        .all()
    )


@router.get("/{business_id}", response_model=BusinessOut)
def buscar_business(
    business_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    company = _get_user_company(db, current_user.id)
    business = (
        db.query(Business)
        .filter(
            Business.id == business_id,
            Business.company_id == company.id,
            Business.deleted_at.is_(None),
        )
        .first()
    )
    if not business:
        raise HTTPException(status_code=404, detail="Business não encontrado")
    return business


@router.put("/{business_id}", response_model=BusinessOut)
def atualizar_business(
    business_id: int,
    payload: BusinessUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas usuários com role 'admin' podem editar um business.",
        )
    company = _get_user_company(db, current_user.id)
    business = (
        db.query(Business)
        .filter(
            Business.id == business_id,
            Business.company_id == company.id,
            Business.deleted_at.is_(None),
        )
        .first()
    )
    if not business:
        raise HTTPException(status_code=404, detail="Business não encontrado")

    if payload.name is not None:     business.name = payload.name
    if payload.document is not None: business.document = payload.document

    db.commit()
    db.refresh(business)
    return business


@router.delete("/{business_id}", status_code=status.HTTP_204_NO_CONTENT)
def deletar_business(
    business_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas usuários com role 'admin' podem excluir um business.",
        )
    company = _get_user_company(db, current_user.id)
    business = (
        db.query(Business)
        .filter(
            Business.id == business_id,
            Business.company_id == company.id,
            Business.deleted_at.is_(None),
        )
        .first()
    )
    if not business:
        raise HTTPException(status_code=404, detail="Business não encontrado")

    business.deleted_at = func.now()
    db.commit()