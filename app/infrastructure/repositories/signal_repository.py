from __future__ import annotations
"""Signal Repository - MySQL Implementation.

Implements ISignalRepository using existing signal_flag_pool table.
"""


import logging
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import select, delete, func
from sqlalchemy.orm import Session

from app.domain.base import Entity
from app.domain.repositories.signal import ISignalRepository, Signal, SignalType


from app.core.logger import get_logger

logger = get_logger(__name__)


class MySQLSignalRepository(ISignalRepository):
    """MySQL implementation of signal repository."""
    
    SIGNAL_TYPE_MAP = {
        "buy": SignalType.BUY,
        "sell": SignalType.SELL,
        "hold": SignalType.HOLD,
        "strong_buy": SignalType.STRONG_BUY,
        "strong_sell": SignalType.STRONG_SELL,
    }
    
    def __init__(self, session_factory):
        self._session_factory = session_factory
    
    def _get_session(self) -> Session:
        return self._session_factory()
    
    def _row_to_signal(self, row) -> Signal:
        signal_type = self.SIGNAL_TYPE_MAP.get(row.get("signal_type", "hold"), SignalType.HOLD)
        return Signal(
            stock_code=row.get("stock_code", ""),
            signal_type=signal_type,
            source=row.get("source", "system"),
            confidence=row.get("confidence", 0.5),
            reason=row.get("reason", ""),
        )
    
    def get_by_stock(self, stock_code: str, limit: int = 10) -> list[Signal]:
        """Get signals for a stock from signal_flag_pool table."""
        with self._get_session() as session:
            from app.infrastructure.database.models.advanced import SignalFlagPool
            
            stmt = (
                select(SignalFlagPool)
                .where(SignalFlagPool.stock_code == stock_code)
                .order_by(SignalFlagPool.pool_date.desc())
                .limit(limit)
            )
            results = session.execute(stmt).scalars().all()
            
            signals = []
            for r in results:
                signal_type = self.SIGNAL_TYPE_MAP.get(r.signal_type, SignalType.HOLD)
                signals.append(Signal(
                    stock_code=r.stock_code,
                    signal_type=signal_type,
                    source=r.source or "system",
                    confidence=r.confidence or 0.5,
                    reason=r.reason or "",
                ))
            return signals
    
    def get_active(self, limit: int = 100) -> list[Signal]:
        """Get active signals (from recent pool dates)."""
        with self._get_session() as session:
            from app.infrastructure.database.models.advanced import SignalFlagPool
            
            recent_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
            
            stmt = (
                select(SignalFlagPool)
                .where(SignalFlagPool.pool_date >= recent_date)
                .order_by(SignalFlagPool.pool_date.desc(), SignalFlagPool.confidence.desc())
                .limit(limit)
            )
            results = session.execute(stmt).scalars().all()
            
            signals = []
            for r in results:
                signal_type = self.SIGNAL_TYPE_MAP.get(r.signal_type, SignalType.HOLD)
                signals.append(Signal(
                    stock_code=r.stock_code,
                    signal_type=signal_type,
                    source=r.source or "system",
                    confidence=r.confidence or 0.5,
                    reason=r.reason or "",
                ))
            return signals
    
    def save(self, signal: Signal) -> Signal:
        """Persist a signal to the signal_flag_pool table.

        Uses upsert semantics: if a signal with the same stock_code,
        source, and signal_type already exists for today's pool_date,
        it is updated; otherwise a new row is inserted.
        """
        session = self._get_session()
        try:
            from app.infrastructure.database.models.advanced import SignalFlagPool
            from sqlalchemy import select

            today = datetime.now().strftime("%Y-%m-%d")
            # Serialize reason/confidence into JSON-compatible extra fields
            extra = {
                "reason": signal.reason,
                "source_detail": signal.source,
            }
            if signal.expires_at:
                extra["expires_at"] = signal.expires_at.isoformat()

            stmt = (
                select(SignalFlagPool)
                .where(
                    SignalFlagPool.pool_date == today,
                    SignalFlagPool.code == signal.stock_code,
                )
            )
            row = session.execute(stmt).scalar_one_or_none()
            if row:
                # Update existing signal row
                row.signal_strategies = signal.signal_type.value
                row.extra_snapshot = str(extra)
            else:
                # Insert new signal row
                new_row = SignalFlagPool(
                    pool_date=today,
                    code=signal.stock_code,
                    signal_strategies=signal.signal_type.value,
                    extra_snapshot=str(extra),
                )
                session.add(new_row)

            session.commit()
            return signal
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
    
    def delete_expired(self) -> int:
        """Delete expired signals."""
        with self._get_session() as session:
            from app.infrastructure.database.models.advanced import SignalFlagPool
            
            cutoff_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
            
            stmt = delete(SignalFlagPool).where(SignalFlagPool.pool_date < cutoff_date)
            result = session.execute(stmt)
            session.commit()
            return result.rowcount


__all__ = ["MySQLSignalRepository"]