"""
Endpoints de Empresa — CRUD completo
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.db.database import get_db
from app.models.empresa import Empresa
from app.schemas.empresa import EmpresaCreate, EmpresaUpdate, EmpresaOut
from app.core.deps import get_current_user
from app.models.user import User

router = APIRouter(prefix="/api/v1/empresa", tags=["empresa"])


@router.post("/", response_model=EmpresaOut, status_code=status.HTTP_201_CREATED)
def criar_empresa(
    payload: EmpresaCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Cria uma nova empresa para o usuário autenticado"""
    empresa = Empresa(
        user_id=current_user.id,
        nome=payload.nome,
        cnpj=payload.cnpj,
        estado=payload.estado.upper(),
        regime_tributario=payload.regime_tributario,
    )
    db.add(empresa)
    db.commit()
    db.refresh(empresa)
    return empresa


@router.get("/", response_model=List[EmpresaOut])
def listar_empresas(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Lista todas as empresas do usuário autenticado"""
    return (
        db.query(Empresa)
        .filter(Empresa.user_id == current_user.id)
        .order_by(Empresa.created_at.desc())
        .all()
    )


@router.get("/{empresa_id}", response_model=EmpresaOut)
def buscar_empresa(
    empresa_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Busca uma empresa pelo ID"""
    empresa = (
        db.query(Empresa)
        .filter(Empresa.id == empresa_id, Empresa.user_id == current_user.id)
        .first()
    )
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")
    return empresa


@router.put("/{empresa_id}", response_model=EmpresaOut)
def atualizar_empresa(
    empresa_id: int,
    payload: EmpresaUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Atualiza dados de uma empresa"""
    empresa = (
        db.query(Empresa)
        .filter(Empresa.id == empresa_id, Empresa.user_id == current_user.id)
        .first()
    )
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")

    if payload.nome:
        empresa.nome = payload.nome
    if payload.cnpj:
        empresa.cnpj = payload.cnpj
    if payload.estado:
        empresa.estado = payload.estado.upper()
    if payload.regime_tributario:
        empresa.regime_tributario = payload.regime_tributario

    db.commit()
    db.refresh(empresa)
    return empresa


@router.delete("/{empresa_id}", status_code=status.HTTP_204_NO_CONTENT)
def deletar_empresa(
    empresa_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Remove uma empresa"""
    empresa = (
        db.query(Empresa)
        .filter(Empresa.id == empresa_id, Empresa.user_id == current_user.id)
        .first()
    )
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")

    db.delete(empresa)
    db.commit()