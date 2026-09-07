"""AI-советы для дашборда.

Советы хранятся отдельно для двух режимов дашборда — ``scope="family"``
(общие для семьи) и ``scope="personal"`` (личные, видны только владельцу).
Генерируются от имени текущего пользователя (используется его AI-ключ или
серверный ключ). Список советов фильтруется по ``scope`` и перелистывается
на дашборде в блоке «Совет от AI».
"""

from typing import List
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from app.ai import (
    AIError,
    decrypt_key,
    generate_advice,
    has_server_gigachat_key,
    is_supported,
    server_gigachat_key,
)
from app.database import get_db
from app.models import AiAdvice, User
from app.routers.transactions import _require_membership
from app.security import get_current_user
from app.services.analytics import get_family_summary
from app.services.ai_advices import SCOPE_FAMILY, SCOPE_PERSONAL

router = APIRouter(prefix="/families", tags=["ai"])


class AdviceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    family_id: UUID
    user_id: UUID
    scope: str = SCOPE_FAMILY
    text: str
    provider: str | None = None
    created_at: datetime | None = None


class AdviceCreated(BaseModel):
    advice: AdviceOut


def _advice_to_out(advice: AiAdvice) -> AdviceOut:
    return AdviceOut(
        id=advice.id,
        family_id=advice.family_id,
        user_id=advice.user_id,
        scope=advice.scope,
        text=advice.text,
        provider=advice.provider,
        created_at=advice.created_at,
    )


@router.get(
    "/{family_id}/advices",
    response_model=List[AdviceOut],
    summary="Список AI-советов (свежие сверху), отфильтрован по scope",
)
def list_advices(
    family_id: UUID,
    scope: str | None = Query(default=None, pattern="^(family|personal)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_membership(db, family_id, current_user.id)
    query = db.query(AiAdvice).filter(AiAdvice.family_id == family_id)
    if scope == SCOPE_FAMILY:
        query = query.filter(AiAdvice.scope == SCOPE_FAMILY)
    elif scope == SCOPE_PERSONAL:
        query = query.filter(
            AiAdvice.user_id == current_user.id,
            AiAdvice.scope == SCOPE_PERSONAL,
        )
    else:
        query = query.filter(
            or_(
                AiAdvice.scope == SCOPE_FAMILY,
                and_(
                    AiAdvice.user_id == current_user.id,
                    AiAdvice.scope == SCOPE_PERSONAL,
                ),
            )
        )
    advices = query.order_by(AiAdvice.created_at.desc(), AiAdvice.id.desc()).all()
    return [_advice_to_out(a) for a in advices]


@router.post(
    "/{family_id}/advices",
    response_model=AdviceCreated,
    status_code=status.HTTP_201_CREATED,
    summary="Сгенерировать новый AI-совет для режима (scope)",
)
def create_advice(
    family_id: UUID,
    scope: str = Query(default=SCOPE_FAMILY, pattern="^(family|personal)$"),
    replace: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_membership(db, family_id, current_user.id)

    if has_server_gigachat_key():
        api_key = server_gigachat_key()
        provider = "gigachat"
        base_url = None
    else:
        if not current_user.ai_api_key_encrypted:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="У вас не сохранён AI-ключ. Добавьте его в профиле.",
            )
        if not is_supported(current_user.ai_provider):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="AI-провайдер не настроен. Укажите его в профиле.",
            )
        api_key = decrypt_key(current_user.ai_api_key_encrypted)
        provider = current_user.ai_provider
        base_url = None

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Не удалось получить AI-ключ. Обратитесь к администратору.",
        )

    summary = get_family_summary(
        db,
        family_id,
        current_user.id,
        filter_user_id=current_user.id if scope == SCOPE_PERSONAL else None,
    )
    try:
        text = generate_advice(
            summary,
            api_key=api_key,
            provider=provider,
            base_url=base_url,
        )
    except AIError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc

    if replace:
        if scope == SCOPE_PERSONAL:
            db.query(AiAdvice).filter(
                AiAdvice.family_id == family_id,
                AiAdvice.user_id == current_user.id,
                AiAdvice.scope == SCOPE_PERSONAL,
            ).delete(synchronize_session=False)
        else:
            db.query(AiAdvice).filter(
                AiAdvice.family_id == family_id,
                AiAdvice.scope == SCOPE_FAMILY,
            ).delete(synchronize_session=False)

    advice = AiAdvice(
        family_id=family_id,
        user_id=current_user.id,
        scope=scope,
        text=text.strip(),
        provider=provider,
    )
    db.add(advice)
    db.commit()
    db.refresh(advice)
    return AdviceCreated(advice=_advice_to_out(advice))
