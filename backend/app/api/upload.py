"""
Endpoints de upload XLSX - Faturamento e Anúncios
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy.orm import Session
from pathlib import Path
import uuid
from datetime import datetime
import logging
import json

from app.db.database import get_db
from app.models.user import User
from app.models.upload import Upload
from app.models.empresa import Empresa                          # ← NOVO
from app.core.deps import get_current_user
from app.services.xlsx_processor import process_xlsx_to_parquet
from app.services.anuncios_processor import process_anuncios_to_parquet

router = APIRouter(prefix="/api/v1/upload", tags=["upload"])
logger = logging.getLogger(__name__)

@router.post("/faturamento")
async def upload_faturamento(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Upload de planilha de faturamento"""

    if not file.filename.endswith('.xlsx'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Apenas arquivos XLSX são permitidos"
        )

    # ── Busca empresa do usuário para obter estado de origem ──
    empresa = (
        db.query(Empresa)
        .filter(Empresa.user_id == current_user.id)
        .first()
    )

    if not empresa:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cadastre uma empresa antes de fazer o upload. "
                   "O estado da empresa é necessário para o cálculo de ICMS."
        )

    estado_origem = empresa.estado
    logger.info(f"🏢 Empresa: {empresa.nome} | Estado origem: {estado_origem}")

    # ── Deleta uploads anteriores de faturamento deste usuário ─
    previous_uploads = (
        db.query(Upload)
        .filter(
            Upload.user_id == current_user.id,
            Upload.upload_type == "faturamento"
        )
        .all()
    )

    for old_upload in previous_uploads:
        try:
            if old_upload.file_path and Path(old_upload.file_path).exists():
                Path(old_upload.file_path).unlink()
                logger.info(f"🗑️ Arquivo deletado: {old_upload.file_path}")

            if old_upload.parquet_path and Path(old_upload.parquet_path).exists():
                Path(old_upload.parquet_path).unlink()
                logger.info(f"🗑️ Parquet deletado: {old_upload.parquet_path}")
        except Exception as e:
            logger.warning(f"⚠️ Erro ao deletar arquivos: {e}")

        db.delete(old_upload)

    db.commit()
    logger.info(f"✅ {len(previous_uploads)} upload(s) anterior(es) removido(s)")

    # ── Gera nome único e salva arquivo ───────────────────────
    file_id   = str(uuid.uuid4())
    filename  = f"{file_id}_{file.filename}"
    file_path = Path("data/raw/faturamento") / filename

    file_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        with open(file_path, "wb") as f:
            f.write(await file.read())
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao salvar: {str(e)}"
        )

    # ── Cria registro no banco ────────────────────────────────
    new_upload = Upload(
        user_id=current_user.id,
        upload_type="faturamento",
        filename=filename,
        original_filename=file.filename,
        file_path=str(file_path),
        processing_status="pending"
    )

    db.add(new_upload)
    db.commit()
    db.refresh(new_upload)

    # ── Processa XLSX com cálculo de ICMS ─────────────────────
    try:
        result = process_xlsx_to_parquet(
            str(file_path),
            current_user.id,
            estado_origem=estado_origem,        # ← NOVO
        )

        new_upload.processing_status = "completed"
        new_upload.rows_processed    = result["rows"]
        new_upload.parquet_path      = result["parquet_path"]
        new_upload.metrics_json      = json.dumps(result.get("summary", {}))
        new_upload.processed_at      = datetime.utcnow()

        db.commit()
        db.refresh(new_upload)

    except Exception as e:
        logger.error(f"Erro: {e}")
        new_upload.processing_status = "failed"
        new_upload.error_message     = str(e)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao processar: {str(e)}"
        )

    return {
        "id":          new_upload.id,
        "upload_type": "faturamento",
        "status":      new_upload.processing_status,
        "rows":        new_upload.rows_processed,
        "message":     "✅ Planilha de faturamento processada com sucesso!",
        "info":        f"Upload anterior substituído. Mostrando novos dados.",
    }


@router.post("/anuncios")
async def upload_anuncios(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Upload de planilha de anúncios"""

    if not file.filename.endswith('.xlsx'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Apenas arquivos XLSX são permitidos"
        )

    # Gera nome único
    file_id   = str(uuid.uuid4())
    filename  = f"{file_id}_{file.filename}"
    file_path = Path("data/raw/anuncios") / filename

    file_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        with open(file_path, "wb") as f:
            f.write(await file.read())
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao salvar: {str(e)}"
        )

    new_upload = Upload(
        user_id=current_user.id,
        upload_type="anuncios",
        filename=filename,
        original_filename=file.filename,
        file_path=str(file_path),
        processing_status="pending"
    )

    db.add(new_upload)
    db.commit()
    db.refresh(new_upload)

    try:
        result = process_anuncios_to_parquet(str(file_path), current_user.id)

        new_upload.processing_status = "completed"
        new_upload.rows_processed    = result["rows"]
        new_upload.parquet_path      = result["parquet_path"]
        new_upload.metrics_json      = json.dumps(result.get("metrics", {}))
        new_upload.processed_at      = datetime.utcnow()

        db.commit()
        db.refresh(new_upload)

    except Exception as e:
        logger.error(f"Erro: {e}")
        new_upload.processing_status = "failed"
        new_upload.error_message     = str(e)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao processar: {str(e)}"
        )

    return {
        "id":          new_upload.id,
        "upload_type": "anuncios",
        "status":      new_upload.processing_status,
        "rows":        new_upload.rows_processed,
        "metrics":     result.get("metrics", {}),
        "message":     "✅ Planilha de anúncios processada!"
    }


@router.get("/list/{upload_type}")
def list_uploads_by_type(
    upload_type: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Lista uploads por tipo"""
    uploads = (
        db.query(Upload)
        .filter(
            Upload.user_id == current_user.id,
            Upload.upload_type == upload_type
        )
        .order_by(Upload.uploaded_at.desc())
        .limit(10)
        .all()
    )

    return [
        {
            "id":          u.id,
            "filename":    u.original_filename,
            "status":      u.processing_status,
            "rows":        u.rows_processed,
            "uploaded_at": u.uploaded_at.isoformat() if u.uploaded_at else None,
        }
        for u in uploads
    ]