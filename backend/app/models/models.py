import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    telegram_id = Column(String(255), unique=True, nullable=True, index=True)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    family_memberships = relationship("FamilyMember", back_populates="user")
    transactions = relationship("Transaction", back_populates="user")
    corrections = relationship("UserCorrection", back_populates="user")


class Family(Base):
    __tablename__ = "families"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    invite_code = Column(String(32), unique=True, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    members = relationship("FamilyMember", back_populates="family")
    transactions = relationship("Transaction", back_populates="family")


class FamilyMember(Base):
    __tablename__ = "family_members"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    family_id = Column(UUID(as_uuid=True), ForeignKey("families.id"), nullable=False)
    role = Column(String(50), default="member")
    joined_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="family_memberships")
    family = relationship("Family", back_populates="members")


class Category(Base):
    __tablename__ = "categories"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False, unique=True)
    rules = Column(Text, nullable=True)  # JSON-правила для автоматической категоризации

    transactions = relationship("Transaction", back_populates="category")


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    family_id = Column(UUID(as_uuid=True), ForeignKey("families.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    category_id = Column(UUID(as_uuid=True), ForeignKey("categories.id"), nullable=True)
    date = Column(DateTime, nullable=False)
    amount = Column(Float, nullable=False)
    original_description = Column(Text, nullable=False)
    cleaned_description = Column(Text, nullable=True)
    source_file = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    family = relationship("Family", back_populates="transactions")
    user = relationship("User", back_populates="transactions")
    category = relationship("Category", back_populates="transactions")
    corrections = relationship("UserCorrection", back_populates="transaction")


class BotLink(Base):
    __tablename__ = "bot_links"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code = Column(String(16), unique=True, nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    telegram_id = Column(String(255), nullable=True)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User")


class UserCorrection(Base):
    __tablename__ = "user_corrections"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    transaction_id = Column(UUID(as_uuid=True), ForeignKey("transactions.id"), nullable=False)
    field_name = Column(String(100), nullable=False)  # category или cleaned_description
    old_value = Column(Text, nullable=True)
    new_value = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="corrections")
    transaction = relationship("Transaction", back_populates="corrections")