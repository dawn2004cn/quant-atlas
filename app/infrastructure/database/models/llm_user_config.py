"""ORM model: per-user LLM configuration storage."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import String, Integer, Float, SmallInteger, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column, MappedAsDataclass

from app.infrastructure.database.orm import Base


class UserLlmConfig(MappedAsDataclass, Base):
    """User-specific LLM provider configuration.

    Each row represents one provider configuration for a user.
    Primary uniqueness constraint: (user_id, provider).
    System-wide defaults are stored with user_id=0.
    """

    __tablename__ = "user_llm_configs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    model_name: Mapped[str] = mapped_column(String(128), nullable=False)
    api_key_encrypted: Mapped[str] = mapped_column(String(512), nullable=False)
    temperature: Mapped[float] = mapped_column(Float, default=0.2)
    max_tokens: Mapped[int] = mapped_column(Integer, default=4096)
    timeout_sec: Mapped[int] = mapped_column(Integer, default=120)
    base_url: Mapped[str | None] = mapped_column(String(512), default=None)
    model_alias: Mapped[str | None] = mapped_column(String(64), default=None)
    fallback_chain_json: Mapped[str | None] = mapped_column(Text, default=None)
    is_active: Mapped[int] = mapped_column(SmallInteger, default=1)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now
    )
