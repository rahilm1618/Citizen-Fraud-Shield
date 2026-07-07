"""
SQLAlchemy ORM models for Citizen Fraud Shield.

Tables:
  - users              Citizen / law-enforcement / admin accounts
  - scam_patterns      Reference scam scripts (RAG corpus)
  - fraud_sessions     Each citizen submission + AI verdict
  - session_messages    Follow-up chat messages within a session
  - fraud_entities      Extracted entities (phone, bank account, UPI, name)
  - fraud_links         Links between sessions and entities (graph edges)
"""

import uuid
from datetime import datetime, timezone

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    ARRAY,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


# ── Users ─────────────────────────────────────────────────────────────────────
class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    role: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="citizen",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )

    # Relationships
    sessions: Mapped[list["FraudSession"]] = relationship(back_populates="user")

    __table_args__ = (
        CheckConstraint(
            "role IN ('citizen', 'law_enforcement', 'admin')",
            name="ck_users_role",
        ),
    )


# ── Scam Patterns (RAG Corpus) ───────────────────────────────────────────────
class ScamPattern(Base):
    __tablename__ = "scam_patterns"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    script_text: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str | None] = mapped_column(String(50), nullable=True)
    embedding = mapped_column(Vector(384), nullable=True)
    source: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )


# ── Fraud Sessions ───────────────────────────────────────────────────────────
class FraudSession(Base):
    __tablename__ = "fraud_sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    transcript_text: Mapped[str] = mapped_column(Text, nullable=False)
    risk_score: Mapped[int] = mapped_column(Integer, nullable=False)
    ai_explanation: Mapped[str] = mapped_column(Text, nullable=False)
    matched_pattern_ids = mapped_column(
        ARRAY(UUID(as_uuid=True)), nullable=True
    )
    embedding = mapped_column(Vector(384), nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), default="flagged", nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    user: Mapped[User | None] = relationship(back_populates="sessions")
    messages: Mapped[list["SessionMessage"]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )
    fraud_links: Mapped[list["FraudLink"]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )


# ── Session Messages (Follow-up Q&A) ─────────────────────────────────────────
class SessionMessage(Base):
    __tablename__ = "session_messages"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("fraud_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    role: Mapped[str] = mapped_column(String(10), nullable=False)  # 'user' | 'assistant'
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )

    # Relationships
    session: Mapped[FraudSession] = relationship(back_populates="messages")


# ── Fraud Entities (Graph Nodes) ──────────────────────────────────────────────
class FraudEntity(Base):
    __tablename__ = "fraud_entities"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    entity_type: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # 'phone', 'bank_account', 'upi_id', 'name'
    entity_value: Mapped[str] = mapped_column(String(255), nullable=False)
    first_seen: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    report_count: Mapped[int] = mapped_column(Integer, default=1)

    # Relationships
    fraud_links: Mapped[list["FraudLink"]] = relationship(
        back_populates="entity", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("entity_type", "entity_value", name="uq_entity_type_value"),
    )


# ── Fraud Links (Graph Edges) ────────────────────────────────────────────────
class FraudLink(Base):
    __tablename__ = "fraud_links"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("fraud_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    entity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("fraud_entities.id", ondelete="CASCADE"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )

    # Relationships
    session: Mapped[FraudSession] = relationship(back_populates="fraud_links")
    entity: Mapped[FraudEntity] = relationship(back_populates="fraud_links")


# ── Indexes (created after table definitions) ────────────────────────────────
# pgvector cosine similarity indexes — will be created when enough rows exist
# (IVFFlat requires training data; we create them in seed step or via migration)
# For now, exact search works fine with small datasets.
