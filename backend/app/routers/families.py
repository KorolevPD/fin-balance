import secrets
from datetime import datetime
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Family, FamilyMember, Transaction, User
from app.security import get_current_user

router = APIRouter(prefix="/families", tags=["families"])

MAX_FAMILY_MEMBERS = 5

_INVITE_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"


def _generate_invite_code() -> str:
    return "".join(secrets.choice(_INVITE_ALPHABET) for _ in range(8))


def _unique_invite_code(db: Session) -> str:
    for _ in range(10):
        code = _generate_invite_code()
        exists = db.query(Family).filter(Family.invite_code == code).first()
        if exists is None:
            return code
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Не удалось сгенерировать уникальный код приглашения",
    )


def create_default_family(db: Session, user: User) -> Family:
    """Создать семью по умолчанию для пользователя (владелец)."""
    family = Family(invite_code=_unique_invite_code(db))
    db.add(family)
    db.flush()
    db.add(FamilyMember(user_id=user.id, family_id=family.id, role="owner"))
    return family


class FamilyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    invite_code: str
    created_at: datetime


class FamilyJoin(BaseModel):
    invite_code: str = Field(min_length=1, max_length=32)


class MemberOut(BaseModel):
    user_id: UUID
    email: str
    name: str | None = None
    role: str
    joined_at: datetime


@router.post(
    "/join",
    response_model=FamilyOut,
    summary="Вступление в семью по коду (семьи объединяются)",
)
def join_family(
    payload: FamilyJoin,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    code = payload.invite_code.strip().upper()
    target = db.query(Family).filter(Family.invite_code == code).first()
    if target is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Семья с таким кодом не найдена",
        )

    memberships = (
        db.query(FamilyMember)
        .filter(FamilyMember.user_id == current_user.id)
        .all()
    )
    if any(membership.family_id == target.id for membership in memberships):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Вы уже участник этой семьи",
        )

    source_ids = [membership.family_id for membership in memberships]
    if source_ids:
        source_members_count = (
            db.query(FamilyMember)
            .filter(FamilyMember.family_id.in_(source_ids))
            .count()
        )
    else:
        source_members_count = 0
    target_members_count = (
        db.query(FamilyMember)
        .filter(FamilyMember.family_id == target.id)
        .count()
    )

    if target_members_count + source_members_count > MAX_FAMILY_MEMBERS:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"В семье может быть не более {MAX_FAMILY_MEMBERS} участников",
        )

    existing_target_user_ids = {
        member.user_id
        for member in db.query(FamilyMember)
        .filter(FamilyMember.family_id == target.id)
        .all()
    }
    for source_id in source_ids:
        source_members = (
            db.query(FamilyMember)
            .filter(FamilyMember.family_id == source_id)
            .all()
        )
        for member in source_members:
            if member.user_id not in existing_target_user_ids:
                if member.user_id == current_user.id:
                    member.role = "member"
                member.family_id = target.id
                existing_target_user_ids.add(member.user_id)
            else:
                db.delete(member)
        db.query(Transaction).filter(Transaction.family_id == source_id).update(
            {Transaction.family_id: target.id}, synchronize_session=False
        )
        db.flush()
        source = db.query(Family).filter(Family.id == source_id).first()
        if source is not None:
            db.delete(source)

    if current_user.id not in existing_target_user_ids:
        db.add(
            FamilyMember(
                user_id=current_user.id,
                family_id=target.id,
                role="member",
            )
        )
    db.commit()
    db.refresh(target)
    return target


@router.get(
    "/my",
    response_model=List[FamilyOut],
    summary="Список семей текущего пользователя",
)
def my_families(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    memberships = (
        db.query(FamilyMember)
        .filter(FamilyMember.user_id == current_user.id)
        .all()
    )
    families = []
    for membership in memberships:
        family = db.query(Family).filter(Family.id == membership.family_id).first()
        if family is not None:
            families.append(family)
    return families


@router.get(
    "/{family_id}/members",
    response_model=List[MemberOut],
    summary="Список участников семьи",
)
def list_members(
    family_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    family = db.query(Family).filter(Family.id == family_id).first()
    if family is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Семья не найдена",
        )
    membership = (
        db.query(FamilyMember)
        .filter(
            FamilyMember.family_id == family_id,
            FamilyMember.user_id == current_user.id,
        )
        .first()
    )
    if membership is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Нет доступа к этой семье",
        )
    members = db.query(FamilyMember).filter(FamilyMember.family_id == family_id).all()
    return [
        MemberOut(
            user_id=member.user_id,
            email=member.user.email,
            name=member.user.name,
            role=member.role,
            joined_at=member.joined_at,
        )
        for member in members
    ]
