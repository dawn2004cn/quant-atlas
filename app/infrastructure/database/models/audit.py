"""ORM models for Audit Trail — tamper-evident hash chain stored in DB."""

from __future__ import annotations

from sqlalchemy import Double, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..orm import Base


class AuditEvent(Base):
    """Immutable audit event with tamper-evident hash chain properties.

    Each row carries content_hash (SHA-256 of the payload) and chain_hash
    (SHA-256 of previous_hash + content_hash), forming a linked structure
    analogous to a blockchain.
    """

    __tablename__ = "audit_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    snapshot_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    order_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    symbol: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(16), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    price: Mapped[float] = mapped_column(Double, nullable=False)
    ai_evidence_json: Mapped[str] = mapped_column(Text, default="{}")
    factor_values_json: Mapped[str] = mapped_column(Text, default="{}")
    risk_assessment_json: Mapped[str] = mapped_column(Text, default="{}")
    compliance_result_json: Mapped[str] = mapped_column(Text, default="{}")
    timestamp: Mapped[str] = mapped_column(String(64), default="", index=True)
    previous_hash: Mapped[str] = mapped_column(String(64), default="genesis")
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    chain_hash: Mapped[str] = mapped_column(String(64), nullable=False)

    __table_args__ = (
        # P1: Multi-column filter for audit query service
        Index("idx_audit_usertime", "user_id", "symbol", "timestamp"),
    )

    def __repr__(self) -> str:
        return f"<AuditEvent {self.snapshot_id} order={self.order_id} {self.action} {self.symbol}>"
