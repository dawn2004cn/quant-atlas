"""ORM models for Compliance Rules and violation logging."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Double, ForeignKey, Index, Integer, SmallInteger, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..orm import Base


class ComplianceRule(Base):
    """Persisted compliance rules for pre-trade checks.

    Covers blacklist, single-position limits, sector concentration,
    frequency limits, and other guardrail checks.
    """

    __tablename__ = "compliance_rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    rule_code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    rule_type: Mapped[str] = mapped_column(String(32), nullable=False)
    target: Mapped[str] = mapped_column(String(128), default="*")
    limit_value: Mapped[float] = mapped_column(Double, default=0.0)
    enabled: Mapped[int] = mapped_column(SmallInteger, default=1)
    description: Mapped[str | None] = mapped_column(String(256))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime)

    def __repr__(self) -> str:
        return f"<ComplianceRule {self.rule_code} target={self.target} enabled={bool(self.enabled)}>"


class ComplianceViolationLog(Base):
    """Log of compliance rule violations — appended on every failed pre-trade check."""

    __tablename__ = "compliance_violations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    rule_id: Mapped[int] = mapped_column(ForeignKey("compliance_rules.id"), nullable=False, index=True)
    order_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    symbol: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    violation_detail: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)

    __table_args__ = (
        # P1: Count/list queries filtered by user + date range
        Index("idx_violations_user_date", "user_id", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<Violation order={self.order_id} user={self.user_id} {self.symbol}>"
