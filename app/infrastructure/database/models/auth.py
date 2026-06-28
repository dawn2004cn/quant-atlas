"""ORM models for Authentication and Authorization."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..orm import Base


class Role(Base):
    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    label: Mapped[str] = mapped_column(String(128), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    permissions_json: Mapped[str] = mapped_column(Text, default="{}")

    users: Mapped[list[User]] = relationship("User", back_populates="role_rel", lazy="selectin")


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    role_id: Mapped[int | None] = mapped_column(ForeignKey("roles.id"))
    role: Mapped[str] = mapped_column(String(64), default="viewer")
    wechat_openid: Mapped[str | None] = mapped_column(String(128), index=True)
    display_name: Mapped[str | None] = mapped_column(String(128))
    avatar_url: Mapped[str | None] = mapped_column(String(1024))
    locale: Mapped[str | None] = mapped_column(String(8), default="zh")

    role_rel: Mapped[Role | None] = relationship("Role", back_populates="users")


class UserRoleAssignment(Base):
    """User-to-role assignment with scope (global / team / account)."""

    __tablename__ = "user_role_assignments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True, nullable=False, index=True)
    role_id: Mapped[int] = mapped_column(ForeignKey("roles.id"), nullable=False)
    scope: Mapped[str] = mapped_column(String(32), default="global")
    assigned_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    assigned_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))

    user: Mapped[User] = relationship("User", foreign_keys=[user_id])
    role: Mapped[Role] = relationship("Role")
    assigner: Mapped[User | None] = relationship("User", foreign_keys=[assigned_by])
