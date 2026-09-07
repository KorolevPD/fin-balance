"""Инвалидация и фоновая перегенерация AI-советов.

Советы хранятся отдельно для двух режимов дашборда:
- ``scope="family"`` — общие советы для семьи (видны всем участникам);
- ``scope="personal"`` — личные советы конкретного пользователя (видны
только владельцу).

При любом изменении операций (импорт, правка, удаление) устаревшие советы
группы и пользователя удаляются, после чего в фоне генерируется новый совет
для активного режима (``advice_scope`` из запроса, по умолчанию ``personal``).
"""

from uuid import UUID

from sqlalchemy.orm import Session

from app import database
from app.ai import (
    AIError,
    decrypt_key,
    generate_advice,
    has_server_gigachat_key,
    is_supported,
    server_gigachat_key,
)
from app.models import AiAdvice, User
from app.services.analytics import get_family_summary

SCOPE_FAMILY = "family"
SCOPE_PERSONAL = "personal"


def invalidate_family_advices(db: Session, family_id: UUID) -> None:
    """Удалить семейные советы семьи — устарели при изменении операций."""
    db.query(AiAdvice).filter(
        AiAdvice.family_id == family_id,
        AiAdvice.scope == SCOPE_FAMILY,
    ).delete(synchronize_session=False)


def invalidate_personal_advices(
    db: Session,
    family_id: UUID,
    user_id: UUID,
) -> None:
    """Удалить личные советы пользователя — устарели при изменении операций."""
    db.query(AiAdvice).filter(
        AiAdvice.family_id == family_id,
        AiAdvice.user_id == user_id,
        AiAdvice.scope == SCOPE_PERSONAL,
    ).delete(synchronize_session=False)


def _resolve_ai_key(user: User) -> tuple[str, str, str | None] | None:
    """Вернуть (key, provider, base_url) для генерации совета либо ``None``."""
    if has_server_gigachat_key():
        return server_gigachat_key(), "gigachat", None
    if not user.ai_api_key_encrypted or not is_supported(user.ai_provider):
        return None
    api_key = decrypt_key(user.ai_api_key_encrypted)
    if not api_key:
        return None
    return api_key, user.ai_provider, None


def regenerate_advice_now(
    db: Session,
    *,
    family_id: UUID,
    user_id: UUID,
    scope: str,
) -> None:
    """Синхронно сгенерировать и сохранить совет для заданного режима.

    Без доступного AI-ключа или при ошибке AI совет не создаётся —
    фронтенд покажет пустое состояние с кнопкой «Получить совет».
    """
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        return

    resolved = _resolve_ai_key(user)
    if resolved is None:
        return
    api_key, provider, base_url = resolved

    try:
        summary = get_family_summary(
            db,
            family_id,
            user_id,
            filter_user_id=user_id if scope == SCOPE_PERSONAL else None,
        )
        text = generate_advice(
            summary,
            api_key=api_key,
            provider=provider,
            base_url=base_url,
        )
    except AIError:
        return

    db.add(
        AiAdvice(
            family_id=family_id,
            user_id=user_id,
            scope=scope,
            text=text.strip(),
            provider=provider,
        )
    )
    db.commit()


def regenerate_advice_in_background(
    *,
    family_id: UUID,
    user_id: UUID,
    scope: str,
) -> None:
    """Фоновая перегенерация совета: собственная сессия, ошибки не роняют запрос.

    Используется как BackgroundTasks после изменения операций. Генерация идёт
    после фонового обогащения «Прочее», поэтому совет строится по итоговым
    категориям.
    """
    db = database.SessionLocal()
    try:
        regenerate_advice_now(
            db,
            family_id=family_id,
            user_id=user_id,
            scope=scope,
        )
    except Exception:  # noqa: BLE001 — фон не должен ломать основной запрос
        return
    finally:
        db.close()
