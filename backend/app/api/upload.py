import os
import uuid
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from app.core.deps import get_current_user
from app.models.user import User
from app.services.xlsx_processor import process_xlsx_to_parquet

router = APIRouter(prefix="/api/v1/upload", tags=["upload"])

@router.post("/")
async def upload_xlsx(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    if not file.filename.lower().endswith(".xlsx"):
        raise HTTPException(status_code=400, detail="Envie um arquivo .xlsx")

    raw_dir = "data/raw"
    os.makedirs(raw_dir, exist_ok=True)

    tmp_name = f"{uuid.uuid4()}_{file.filename}"
    raw_path = os.path.join(raw_dir, tmp_name)

    content = await file.read()
    with open(raw_path, "wb") as f:
        f.write(content)

    result = process_xlsx_to_parquet(raw_path, user_id=current_user.id)
    return result