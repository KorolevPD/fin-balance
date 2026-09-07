import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
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
    name = Column(String(255), nullable=True)
    avatar = Column(String(255), nullable=True)
    telegram_id = Column(String(255), unique=True, nullable=True, index=True)
    password_hash = Column(String(255), nullable=False)
    ai_provider = Column(String(50), nullable=True)
    ai_api_key_encrypted = Column(Text, nullable=True)
    ai_base_url = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    family_memberships = relationship("FamilyMember", back_populates="user")
    transactions = relationship("Transaction", back_populates="user")
    corrections = relationship("UserCorrection", back_populates="user")
    advices = relationship("AiAdvice", back_populates="user")


class Family(Base):
    __tablename__ = "families"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    invite_code = Column(String(32), unique=True, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    members = relationship("FamilyMember", back_populates="family")
    transactions = relationship("Transaction", back_populates="family")
    advices = relationship("AiAdvice", back_populates="family")


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
    type = Column(
        String(20), nullable=False, default="expense", server_default="expense"
    )
    original_description = Column(Text, nullable=False)
    cleaned_description = Column(Text, nullable=True)
    is_self_transfer = Column(
        Boolean, nullable=False, default=False, server_default="0"
    )
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
    transaction_id = Column(
        UUID(as_uuid=True), ForeignKey("transactions.id"), nullable=False
    )
    field_name = Column(String(100), nullable=False)  # category или cleaned_description
    old_value = Column(Text, nullable=True)
    new_value = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="corrections")
    transaction = relationship("Transaction", back_populates="corrections")


class AiAdvice(Base):
    __tablename__ = "ai_advices"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    family_id = Column(UUID(as_uuid=True), ForeignKey("families.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    scope = Column(
        String(20), nullable=False, default="family", server_default="family"
    )
    text = Column(Text, nullable=False)
    provider = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    family = relationship("Family", back_populates="advices")
    user = relationship("User", back_populates="advices")
