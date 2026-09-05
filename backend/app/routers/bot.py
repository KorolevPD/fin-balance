import secrets
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import BotLink, User
from app.security import get_current_user

router = APIRouter(prefix="/bot", tags=["bot"])

_LINK_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
_LINK_TTL = timedelta(minutes=15)


def _generate_code() -> str:
    return "".join(secrets.choice(_LINK_ALPHABET) for _ in range(6))


class LinkCodeOut(BaseModel):
    code: str
    expires_in_minutes: int


class LinkConfirm(BaseModel):
    code: str = Field(min_length=1, max_length=16)
    telegram_id: str = Field(min_length=1, max_length=255)


@router.post(
    "/link-code",
    response_model=LinkCodeOut,
    summary="Создание кода привязки Telegram-аккаунта",
)
def create_link_code(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    existing = (
        db.query(BotLink)
        .filter(
            BotLink.user_id == current_user.id,
            BotLink.expires_at > datetime.utcnow(),
        )
        .first()
    )
    if existing is not None:
        return LinkCodeOut(
            code=existing.code,
            expires_in_minutes=int(_LINK_TTL.total_seconds() // 60),
        )

    for _ in range(10):
        code = _generate_code()
        dup = db.query(BotLink).filter(BotLink.code == code).first()
        if dup is None:
            break
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Не удалось сгенерировать уникальный код привязки",
        )

    link = BotLink(
        code=code,
        user_id=current_user.id,
        expires_at=datetime.utcnow() + _LINK_TTL,
    )
    db.add(link)
    db.commit()
    return LinkCodeOut(
        code=code,
        expires_in_minutes=int(_LINK_TTL.total_seconds() // 60),
    )


@router.post(
    "/confirm",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Подтверждение привязки аккаунта по коду",
)
def confirm_link(
    payload: LinkConfirm,
    db: Session = Depends(get_db),
):
    code = payload.code.strip().upper()
    link = db.query(BotLink).filter(BotLink.code == code).first()
    if link is None or link.expires_at < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Код привязки неверный или истёк",
        )
    linked_user = db.query(User).filter(User.id == link.user_id).first()
    if linked_user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь не найден",
        )
    already = (
        db.query(User)
        .filter(User.telegram_id == payload.telegram_id, User.id != linked_user.id)
        .first()
    )
    if already is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Этот Telegram-аккаунт уже привязан к другому пользователю",
        )
    linked_user.telegram_id = payload.telegram_id
    link.telegram_id = payload.telegram_id
    link.expires_at = datetime.utcnow()
    db.commit()


class BotMeOut(BaseModel):
    telegram_id: str
    email: str | None = None
    linked: bool


@router.get(
    "/me",
    response_model=BotMeOut,
    summary="Статус привязки аккаунта Telegram",
)
def me(telegram_id: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.telegram_id == telegram_id).first()
    if user is None:
        return BotMeOut(telegram_id=telegram_id, email=None, linked=False)
    return BotMeOut(telegram_id=telegram_id, email=user.email, linked=True)
