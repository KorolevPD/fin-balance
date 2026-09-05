from datetime import datetime
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.categorization import categorize_transactions
from app.database import get_db
from app.models import FamilyMember, Transaction, User
from app.parsers import parse_csv_bytes
from app.security import get_current_user
from app.services import save_transactions

router = APIRouter(prefix="/families", tags=["transactions"])


class ImportResult(BaseModel):
    family_id: UUID
    user_id: UUID
    parsed: int
    created: int
    duplicates_skipped: int


class TransactionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    family_id: UUID
    user_id: UUID
    category: str | None = None
    date: datetime
    amount: float
    original_description: str
    cleaned_description: str | None = None
    source_file: str | None = None
    created_at: datetime


def _require_membership(
    db: Session,
    family_id: UUID,
    user_id: UUID,
) -> None:
    family = db.query(FamilyMember).filter(
        FamilyMember.family_id == family_id,
        FamilyMember.user_id == user_id,
    )
    if family.first() is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Нет доступа к этой семье",
        )


@router.post(
    "/{family_id}/transactions/import",
    response_model=ImportResult,
    status_code=status.HTTP_201_CREATED,
    summary="Импорт транзакций из CSV",
)
def import_transactions(
    family_id: UUID,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_membership(db, family_id, current_user.id)

    try:
        parsed = categorize_transactions(parse_csv_bytes(file.file.read()))
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Не удалось разобрать файл: {exc}",
        )

    result = save_transactions(
        db,
        family_id=family_id,
        user_id=current_user.id,
        transactions=parsed,
        source_file=file.filename,
    )
    return ImportResult(
        family_id=family_id,
        user_id=current_user.id,
        parsed=len(parsed),
        created=result.created,
        duplicates_skipped=result.duplicates_skipped,
    )


@router.get(
    "/{family_id}/transactions",
    response_model=List[TransactionOut],
    summary="Список транзакций семьи",
)
def list_transactions(
    family_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_membership(db, family_id, current_user.id)
    transactions = (
        db.query(Transaction)
        .filter(Transaction.family_id == family_id)
        .order_by(Transaction.date)
        .all()
    )
    return [
        TransactionOut(
            id=t.id,
            family_id=t.family_id,
            user_id=t.user_id,
            category=t.category.name if t.category is not None else None,
            date=t.date,
            amount=t.amount,
            original_description=t.original_description,
            cleaned_description=t.cleaned_description,
            source_file=t.source_file,
            created_at=t.created_at,
        )
        for t in transactions
    ]
