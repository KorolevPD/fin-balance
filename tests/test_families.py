# -*- coding: utf-8 -*-

from datetime import datetime
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.database import get_db
from app.models import Family, FamilyMember, Transaction, User
from app.security import create_access_token, hash_password
from main import app


@pytest.fixture()
def client_db(session_factory):
    session = session_factory()
    app.dependency_overrides[get_db] = lambda: session
    try:
        yield TestClient(app), session
    finally:
        app.dependency_overrides.pop(get_db, None)
        session.close()


def _user(email="user@example.com"):
    return User(
        email=email,
        password_hash=hash_password("secret1"),
    )


def _token(user) -> str:
    return create_access_token(subject=str(user.id))


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _prepare_user_with_family(session, email, invite_code, role="owner"):
    user = _user(email)
    session.add(user)
    session.flush()
    family = Family(invite_code=invite_code)
    session.add(family)
    session.flush()
    session.add(FamilyMember(user_id=user.id, family_id=family.id, role=role))
    session.commit()
    return user, family


class TestDefaultFamilyOnRegister:
    def test_регистрация_создаёт_семью_владельцу(self, client_db):
        client, session = client_db

        response = client.post(
            "/api/auth/register",
            json={"email": "new@example.com", "password": "secret1"},
        )

        assert response.status_code == 201
        user = session.query(User).filter(User.email == "new@example.com").one()
        memberships = (
            session.query(FamilyMember)
            .filter(FamilyMember.user_id == user.id)
            .all()
        )
        assert len(memberships) == 1
        assert memberships[0].role == "owner"
        family = (
            session.query(Family)
            .filter(Family.id == memberships[0].family_id)
            .one()
        )
        assert family.invite_code

    def test_семья_не_имеет_названия_в_модели(self, session_factory):
        session = session_factory()
        family = Family(invite_code="NONAME01")
        session.add(family)
        session.commit()
        session.refresh(family)

        assert "name" not in Family.__table__.columns
        assert family.invite_code

    def test_семья_без_названия_в_ответе_api(self, client_db):
        client, session = client_db
        user, family = _prepare_user_with_family(
            session, "nofamily@example.com", "NONAME02"
        )

        response = client.get(
            "/api/families/my", headers=_auth(_token(user))
        )

        assert response.status_code == 200
        body = response.json()
        assert len(body) == 1
        assert body[0]["id"] == str(family.id)
        assert "name" not in body[0]
        assert body[0]["invite_code"] == "NONAME02"


class TestJoinMergesFamilies:
    def test_присоединение_объединяет_семьи(self, client_db):
        client, session = client_db
        user_a, family_a = _prepare_user_with_family(
            session, "a@example.com", "AAABBB1", role="owner"
        )
        user_b, family_b = _prepare_user_with_family(
            session, "b@example.com", "BBBDDD2", role="owner"
        )

        response = client.post(
            "/api/families/join",
            json={"invite_code": "AAABBB1"},
            headers=_auth(_token(user_b)),
        )

        assert response.status_code == 200
        assert session.query(Family).filter(Family.id == family_b.id).count() == 0
        members = (
            session.query(FamilyMember)
            .filter(FamilyMember.family_id == family_a.id)
            .all()
        )
        assert len(members) == 2
        memberships_b = (
            session.query(FamilyMember)
            .filter(FamilyMember.user_id == user_b.id)
            .all()
        )
        assert len(memberships_b) == 1
        assert memberships_b[0].family_id == family_a.id
        assert memberships_b[0].role == "member"
        assert memberships_b[0].role != "owner"

    def test_присоединение_переносит_операции_в_семью(self, client_db):
        client, session = client_db
        user_a, family_a = _prepare_user_with_family(
            session, "a@example.com", "AAABBB1", role="owner"
        )
        user_b, family_b = _prepare_user_with_family(
            session, "b@example.com", "BBBDDD2", role="owner"
        )
        session.add(
            Transaction(
                family_id=family_b.id,
                user_id=user_b.id,
                date=datetime(2026, 9, 1),
                amount=100.0,
                original_description="Лента",
            )
        )
        session.commit()

        response = client.post(
            "/api/families/join",
            json={"invite_code": "AAABBB1"},
            headers=_auth(_token(user_b)),
        )

        assert response.status_code == 200
        moved = (
            session.query(Transaction)
            .filter(Transaction.family_id == family_a.id)
            .all()
        )
        assert len(moved) == 1
        assert moved[0].original_description == "Лента"
        assert session.query(Transaction).filter(
            Transaction.family_id == family_b.id
        ).count() == 0

    def test_неверный_код_возвращает_404(self, client_db):
        client, session = client_db
        user_b, _ = _prepare_user_with_family(
            session, "b@example.com", "BBBDDD2", role="owner"
        )

        response = client.post(
            "/api/families/join",
            json={"invite_code": "NOCODE99"},
            headers=_auth(_token(user_b)),
        )

        assert response.status_code == 404

    def test_повторное_вступление_возвращает_409(self, client_db):
        client, session = client_db
        user_a, family_a = _prepare_user_with_family(
            session, "a@example.com", "AAABBB1", role="owner"
        )

        response = client.post(
            "/api/families/join",
            json={"invite_code": "AAABBB1"},
            headers=_auth(_token(user_a)),
        )

        assert response.status_code == 409


class TestFamilySizeLimit:
    def test_присоединение_ограничено_5_участниками(self, client_db):
        client, session = client_db
        owner, family_a = _prepare_user_with_family(
            session, "owner@example.com", "AAABBB1", role="owner"
        )
        for idx in range(4):
            member = User(
                email=f"m{idx}@example.com",
                password_hash=hash_password("secret1"),
            )
            session.add(member)
            session.flush()
            session.add(
                FamilyMember(
                    user_id=member.id, family_id=family_a.id, role="member"
                )
            )
        user_b, family_b = _prepare_user_with_family(
            session, "b@example.com", "BBBDDD2", role="owner"
        )
        session.add(
            User(email="c@example.com", password_hash=hash_password("secret1"))
        )
        session.commit()
        before_b_family = session.query(Family).filter(
            Family.id == family_b.id
        ).count()

        # в семье A уже 5 участников: пользователь B со своей семьёй его не войдёт
        response = client.post(
            "/api/families/join",
            json={"invite_code": "AAABBB1"},
            headers=_auth(_token(user_b)),
        )

        assert response.status_code == 409
        remaining = (
            session.query(Family).filter(Family.id == family_b.id).count()
        )
        assert remaining == before_b_family

    def test_присоединение_при_5_после_объединения_запрещено(self, client_db):
        client, session = client_db
        user_a, family_a = _prepare_user_with_family(
            session, "a@example.com", "AAABBB1", role="owner"
        )
        # семья B из 3 человек присоединяется к семье A из 3 человек -> 6 > 5
        user_b, family_b = _prepare_user_with_family(
            session, "b@example.com", "BBBDDD2", role="owner"
        )
        extra_members = []
        for idx in range(4):
            email = f"extra{idx}@example.com"
            extra = User(email=email, password_hash=hash_password("secret1"))
            session.add(extra)
            session.flush()
            extra_members.append(extra)
        session.add(
            FamilyMember(
                user_id=extra_members[0].id,
                family_id=family_b.id,
                role="member",
            )
        )
        session.add(
            FamilyMember(
                user_id=extra_members[1].id,
                family_id=family_b.id,
                role="member",
            )
        )
        session.add(
            FamilyMember(
                user_id=extra_members[2].id,
                family_id=family_a.id,
                role="member",
            )
        )
        session.add(
            FamilyMember(
                user_id=extra_members[3].id,
                family_id=family_a.id,
                role="member",
            )
        )
        session.commit()

        response = client.post(
            "/api/families/join",
            json={"invite_code": "AAABBB1"},
            headers=_auth(_token(user_b)),
        )

        assert response.status_code == 409
        # семья B не удалена, операция отклонена
        assert session.query(Family).filter(Family.id == family_b.id).count() == 1


class TestDisbandFamily:
    def test_распуск_оставляет_только_владельца_и_удаляет_операции_вышедших(
        self, client_db
    ):
        client, session = client_db
        owner, family = _prepare_user_with_family(
            session, "owner@example.com", "OWNER01", role="owner"
        )
        member_ids = []
        for idx in range(2):
            member = User(
                email=f"m{idx}@example.com",
                password_hash=hash_password("secret1"),
            )
            session.add(member)
            session.flush()
            session.add(
                FamilyMember(
                    user_id=member.id, family_id=family.id, role="member"
                )
            )
            member_ids.append(member.id)
            session.add(
                Transaction(
                    family_id=family.id,
                    user_id=member.id,
                    date=datetime(2026, 9, 1),
                    amount=50.0,
                    original_description=f"Покупка {idx}",
                )
            )
        session.add(
            Transaction(
                family_id=family.id,
                user_id=owner.id,
                date=datetime(2026, 9, 1),
                amount=10.0,
                original_description="Владелец",
            )
        )
        session.commit()

        response = client.post(
            f"/api/families/{family.id}/disband",
            headers=_auth(_token(owner)),
        )

        assert response.status_code == 200
        assert response.json() == {"removed": 2, "remaining": 1}
        remaining = (
            session.query(FamilyMember)
            .filter(FamilyMember.family_id == family.id)
            .all()
        )
        assert len(remaining) == 1
        assert remaining[0].user_id == owner.id
        assert remaining[0].role == "owner"
        transactions = (
            session.query(Transaction)
            .filter(Transaction.family_id == family.id)
            .all()
        )
        assert len(transactions) == 1
        assert transactions[0].user_id == owner.id
        assert (
            session.query(Transaction)
            .filter(Transaction.user_id.in_(member_ids))
            .count()
            == 0
        )

    def test_не_владелец_не_может_распустить(self, client_db):
        client, session = client_db
        owner, family = _prepare_user_with_family(
            session, "owner@example.com", "OWNER02", role="owner"
        )
        member = User(
            email="member@example.com", password_hash=hash_password("secret1")
        )
        session.add(member)
        session.flush()
        session.add(
            FamilyMember(
                user_id=member.id, family_id=family.id, role="member"
            )
        )
        session.commit()

        response = client.post(
            f"/api/families/{family.id}/disband",
            headers=_auth(_token(member)),
        )

        assert response.status_code == 403
        # никто не удалён
        assert (
            session.query(FamilyMember)
            .filter(FamilyMember.family_id == family.id)
            .count()
            == 2
        )

    def test_посторонний_пользователь_получает_403(self, client_db):
        client, session = client_db
        owner, family = _prepare_user_with_family(
            session, "owner@example.com", "OWNER03", role="owner"
        )
        stranger = User(
            email="stranger@example.com", password_hash=hash_password("secret1")
        )
        session.add(stranger)
        session.commit()

        response = client.post(
            f"/api/families/{family.id}/disband",
            headers=_auth(_token(stranger)),
        )

        assert response.status_code == 403

    def test_несуществующая_семья_возвращает_404(self, client_db):
        client, session = client_db
        owner, _ = _prepare_user_with_family(
            session, "owner@example.com", "OWNER04", role="owner"
        )

        response = client.post(
            f"/api/families/{uuid4()}/disband",
            headers=_auth(_token(owner)),
        )

        assert response.status_code == 404

    def test_распуск_при_одном_владельце_ничего_не_удаляет(self, client_db):
        client, session = client_db
        owner, family = _prepare_user_with_family(
            session, "owner@example.com", "OWNER05", role="owner"
        )

        response = client.post(
            f"/api/families/{family.id}/disband",
            headers=_auth(_token(owner)),
        )

        assert response.status_code == 200
        assert response.json() == {"removed": 0, "remaining": 1}
        assert (
            session.query(FamilyMember)
            .filter(FamilyMember.family_id == family.id)
            .count()
            == 1
        )
