from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.user import User
from app.schemas.auth import UserCreate, Token, UserOut
from app.core.security import hash_password, verify_password, create_access_token
from app.core.deps import get_current_user

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

@router.post("/register", status_code=201, response_model=UserOut)
def register(payload: UserCreate, db: Session = Depends(get_db)):
    exists_user = db.query(User).filter(User.username == payload.username).first()
    if exists_user:
        raise HTTPException(status_code=400, detail="Username já existe")

    exists_email = db.query(User).filter(User.email == payload.email).first()
    if exists_email:
        raise HTTPException(status_code=400, detail="Email já existe")

    try:
        password_hash = hash_password(payload.password)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    user = User(
        username=payload.username,
        email=payload.email,
        password_hash=password_hash,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

@router.post("/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciais inválidas")

    token = create_access_token(subject=user.username)
    return {"access_token": token, "token_type": "bearer"}

@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
    return current_user
