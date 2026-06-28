from __future__ import annotations

"""ORM models for multi-tenant collaboration (Quant Atlas 6.0)."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..orm import Base


class Tenant(Base):
    __tablename__ = "tenants"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    slug: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    plan: Mapped[str] = mapped_column(String(32), default="standard", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    teams: Mapped[list[Team]] = relationship("Team", back_populates="tenant", lazy="selectin")


class Team(Base):
    __tablename__ = "teams"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    slug: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    tenant: Mapped[Tenant] = relationship("Tenant", back_populates="teams")
    memberships: Mapped[list[TeamMembership]] = relationship(
        "TeamMembership", back_populates="team", lazy="selectin"
    )

    __table_args__ = (UniqueConstraint("tenant_id", "slug", name="uq_team_tenant_slug"),)


class TeamMembership(Base):
    __tablename__ = "team_memberships"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"), nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(32), default="member", nullable=False)
    joined_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    team: Mapped[Team] = relationship("Team", back_populates="memberships")

    __table_args__ = (UniqueConstraint("team_id", "user_id", name="uq_team_user"),)


class UserLifecycleSettings(Base):
    """Tenant-scoped user lifecycle (notifications, consent, deletion)."""

    __tablename__ = "user_lifecycle_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    notifications_json: Mapped[str | None] = mapped_column(Text)
    privacy_consent_json: Mapped[str | None] = mapped_column(Text)
    deletion_request_json: Mapped[str | None] = mapped_column(Text)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime)

    __table_args__ = (UniqueConstraint("user_id", "tenant_id", name="uq_lifecycle_user_tenant"),)


class TeamBlackboardEntry(Base):
    """Team-shared evidence notes from members and agents."""

    __tablename__ = "team_blackboard_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"), nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    agent_role: Mapped[str] = mapped_column(String(64), default="member", nullable=False)
    symbol: Mapped[str | None] = mapped_column(String(32))
    evidence_key: Mapped[str] = mapped_column(String(128), nullable=False)
    evidence_value: Mapped[str | None] = mapped_column(Text)
    strength: Mapped[str] = mapped_column(String(32), default="moderate")
    narrative: Mapped[str | None] = mapped_column(Text)
    payload_json: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class UserKnowledgeProfile(Base):
    """Tenant-scoped user knowledge graph (migrated from instance JSON)."""

    __tablename__ = "user_knowledge_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    profile_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    updated_at: Mapped[datetime | None] = mapped_column(DateTime)

    __table_args__ = (UniqueConstraint("user_id", "tenant_id", name="uq_knowledge_user_tenant"),)
