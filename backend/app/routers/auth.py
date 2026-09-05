import io
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.security import (
    create_access_token,
    get_current_user,
    hash_password,
    verify_password,
)
from app.storage import (
    AVATAR_ALLOWED_EXTENSIONS,
    AVATAR_CONTENT_TYPES,
    MAX_AVATAR_SIZE,
    avatar_path,
    delete_avatar,
    save_avatar,
)

router = APIRouter(prefix="/auth", tags=["auth"])


class UserCreate(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=6, max_length=128)
    name: str | None = Field(default=None, max_length=255)


class UserLogin(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=1, max_length=128)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    name: str | None = None
    avatar: str | None = None
    telegram_id: str | None = None
    created_at: datetime


class UserUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=255)


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


@router.post(
    "/register",
    response_model=TokenOut,
    status_code=status.HTTP_201_CREATED,
    summary="Регистрация пользователя",
)
def register(payload: UserCreate, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Пользователь с таким email уже существует",
        )
    user = User(
        email=payload.email,
        password_hash=hash_password(payload.password),
        name=(payload.name or "").strip() or None,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    token = create_access_token(subject=str(user.id))
    return {"access_token": token, "token_type": "bearer"}


@router.post(
    "/login",
    response_model=TokenOut,
    summary="Вход по email и паролю",
)
def login(payload: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный email или пароль",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = create_access_token(subject=str(user.id))
    return {"access_token": token, "token_type": "bearer"}


@router.get(
    "/me",
    response_model=UserOut,
    summary="Текущий пользователь",
)
def me(current_user: User = Depends(get_current_user)):
    return current_user


@router.patch(
    "/me",
    response_model=UserOut,
    summary="Обновление профиля текущего пользователя",
)
def update_me(
    payload: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if payload.name is not None:
        current_user.name = payload.name.strip() or None
    db.commit()
    db.refresh(current_user)
    return current_user


@router.post(
    "/me/avatar",
    response_model=UserOut,
    summary="Загрузка фото профиля текущего пользователя",
)
async def upload_avatar(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    filename = file.filename or ""
    suffix = (filename.rsplit(".", 1)[-1].lower() if "." in filename else "")
    ext = f".{suffix}" if suffix else ""
    content_type = (file.content_type or "").lower()
    if ext not in AVATAR_ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Допускаются только изображения: JPG, PNG, WEBP, GIF",
        )
    if content_type not in AVATAR_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Недопустимый тип изображения: {content_type or 'не указан'}",
        )

    data = await file.read()
    if len(data) > MAX_AVATAR_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Размер изображения не должен превышать 5 МБ",
        )

    previous_avatar = current_user.avatar
    stored_name = save_avatar(io.BytesIO(data), filename)
    current_user.avatar = stored_name
    db.commit()
    db.refresh(current_user)

    if previous_avatar:
        delete_avatar(previous_avatar)

    return current_user


@router.get(
    "/me/avatar/{stored_name}",
    summary="Файл фото профиля",
    include_in_schema=False,
)
def get_avatar(stored_name: str):
    path = avatar_path(stored_name)
    if not path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Фото не найдено",
        )
    return FileResponse(path)
