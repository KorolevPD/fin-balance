import secrets
from datetime import datetime
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Family, FamilyMember, User
from app.security import get_current_user

router = APIRouter(prefix="/families", tags=["families"])

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


class FamilyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)


class FamilyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
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
    "",
    response_model=FamilyOut,
    status_code=status.HTTP_201_CREATED,
    summary="Создание семьи",
)
def create_family(
    payload: FamilyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    family = Family(name=payload.name, invite_code=_unique_invite_code(db))
    db.add(family)
    db.flush()
    db.add(
        FamilyMember(
            user_id=current_user.id,
            family_id=family.id,
            role="owner",
        )
    )
    db.commit()
    db.refresh(family)
    return family


@router.post(
    "/join",
    response_model=FamilyOut,
    summary="Присоединение к семье по коду",
)
def join_family(
    payload: FamilyJoin,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    code = payload.invite_code.strip().upper()
    family = db.query(Family).filter(Family.invite_code == code).first()
    if family is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Семья с таким кодом не найдена",
        )
    existing = (
        db.query(FamilyMember)
        .filter(
            FamilyMember.family_id == family.id,
            FamilyMember.user_id == current_user.id,
        )
        .first()
    )
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Вы уже участник этой семьи",
        )
    db.add(
        FamilyMember(
            user_id=current_user.id,
            family_id=family.id,
            role="member",
        )
    )
    db.commit()
    db.refresh(family)
    return family


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
