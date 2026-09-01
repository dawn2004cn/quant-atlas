from __future__ import annotations

"""MySQL implementation of Signal Observation Repository."""

from contextlib import contextmanager
from datetime import datetime
from typing import Any, Iterator

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.logger import get_logger
from app.core.utils.sql_utils import quote_identifier
from app.domain.ports.signal_observation_port import SignalObservationRepository

logger = get_logger(__name__)


class MySQLSignalObservationRepository(SignalObservationRepository):
    """MySQL repository for signal observations and positions."""

    def __init__(self, session_factory) -> None:
        self._session_factory = session_factory

    @contextmanager
    def _session_scope(self, *, commit: bool = False) -> Iterator[Session]:
        """One scoped session per operation — avoids cross-request stale transactions."""
        session = self._session_factory()
        try:
            yield session
            if commit:
                session.commit()
        except Exception:
            try:
                session.rollback()
            except Exception as exc:
                logger.debug("signal observation session rollback failed: %s", exc)
            raise
        finally:
            try:
                session.close()
            except Exception as exc:
                logger.debug("signal observation session close failed: %s", exc)
            remove = getattr(self._session_factory, "remove", None)
            if callable(remove):
                try:
                    remove()
                except Exception as exc:
                    logger.debug("signal observation scoped session remove failed: %s", exc)

    def create_observation(self, data: dict[str, Any]) -> dict[str, Any]:
        """Create a new observation record."""
        with self._session_scope(commit=True) as session:
            session.execute(
                text("""
                    INSERT INTO signal_observations (
                        id, user_id, symbol, market, name, entry_price, current_price,
                        stop_loss, target_price, source, reason, ai_summary,
                        status, trigger_status, created_at, updated_at,
                        closed_at, close_reason, peak_price, trough_price,
                        max_gain_pct, max_drawdown_pct, notes
                    ) VALUES (
                        :id, :user_id, :symbol, :market, :name, :entry_price, :current_price,
                        :stop_loss, :target_price, :source, :reason, :ai_summary,
                        :status, :trigger_status, :created_at, :updated_at,
                        :closed_at, :close_reason, :peak_price, :trough_price,
                        :max_gain_pct, :max_drawdown_pct, :notes
                    )
                """),
                data,
            )
        return data

    _UPDATABLE_OBSERVATION_COLS = frozenset({
        "symbol", "market", "name", "entry_price", "current_price",
        "stop_loss", "target_price", "source", "reason", "ai_summary",
        "status", "trigger_status", "notes", "updated_at",
        "peak_price", "trough_price", "max_gain_pct", "max_drawdown_pct",
        "closed_at", "close_reason",
    })

    def update_observation(self, observation_id: str, user_id: int, data: dict[str, Any]) -> dict[str, Any] | None:
        """Update an observation by ID."""
        data["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        allowed = {k: v for k, v in data.items() if k in self._UPDATABLE_OBSERVATION_COLS}
        sets = ", ".join([f"{quote_identifier(k)} = :{k}" for k in allowed])
        with self._session_scope(commit=True) as session:
            session.execute(
                text(f"UPDATE signal_observations SET {sets} WHERE id = :id AND user_id = :user_id"),
                {**allowed, "id": observation_id, "user_id": user_id},
            )
        return self.get_observation(observation_id, user_id)

    def get_observation(self, observation_id: str, user_id: int) -> dict[str, Any] | None:
        """Get a single observation by ID."""
        with self._session_scope() as session:
            result = session.execute(
                text("SELECT * FROM signal_observations WHERE id = :id AND user_id = :user_id"),
                {"id": observation_id, "user_id": user_id},
            )
            row = result.fetchone()
            if row:
                return dict(row._mapping)
        return None

    def list_observations(
        self,
        user_id: int,
        status: str = "open",
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """List observations for a user with optional status filter."""
        query = "SELECT * FROM signal_observations WHERE user_id = :user_id"
        params: dict[str, Any] = {"user_id": user_id}

        if status and status.lower() not in ("all", "*"):
            query += " AND status = :status"
            params["status"] = status

        query += " ORDER BY updated_at DESC LIMIT :limit"
        params["limit"] = limit

        with self._session_scope() as session:
            result = session.execute(text(query), params)
            return [dict(row._mapping) for row in result.fetchall()]

    def close_observation(
        self,
        observation_id: str,
        user_id: int,
        reason: str = "manual_close",
    ) -> dict[str, Any] | None:
        """Close an observation."""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with self._session_scope(commit=True) as session:
            session.execute(
                text("""
                    UPDATE signal_observations
                    SET status = 'closed', close_reason = :reason,
                        closed_at = :now, updated_at = :now
                    WHERE id = :id AND user_id = :user_id
                """),
                {"id": observation_id, "user_id": user_id, "reason": reason, "now": now},
            )
        return self.get_observation(observation_id, user_id)

    def delete_observation(self, observation_id: str, user_id: int) -> bool:
        """Delete an observation."""
        with self._session_scope(commit=True) as session:
            result = session.execute(
                text("DELETE FROM signal_observations WHERE id = :id AND user_id = :user_id"),
                {"id": observation_id, "user_id": user_id},
            )
            return result.rowcount > 0

    def update_notes(self, observation_id: str, user_id: int, notes: str) -> bool:
        """Update observation notes."""
        with self._session_scope(commit=True) as session:
            session.execute(
                text(
                    "UPDATE signal_observations SET notes = :notes, updated_at = :now "
                    "WHERE id = :id AND user_id = :user_id"
                ),
                {
                    "id": observation_id,
                    "user_id": user_id,
                    "notes": notes,
                    "now": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                },
            )
        return True

    def create_position(self, data: dict[str, Any]) -> dict[str, Any]:
        """Create a position from observation."""
        with self._session_scope(commit=True) as session:
            session.execute(
                text("""
                    INSERT INTO signal_observation_positions (
                        id, user_id, observation_id, symbol, market, name,
                        shares, cost_basis, current_price, total_cost, total_value,
                        pnl, return_pct, max_gain_pct, max_drawdown_pct,
                        source, converted_at, created_at, updated_at
                    ) VALUES (
                        :id, :user_id, :observation_id, :symbol, :market, :name,
                        :shares, :cost_basis, :current_price, :total_cost, :total_value,
                        :pnl, :return_pct, :max_gain_pct, :max_drawdown_pct,
                        :source, :converted_at, :created_at, :updated_at
                    )
                """),
                data,
            )
        return data

    def list_positions(self, user_id: int, limit: int = 100) -> list[dict[str, Any]]:
        """List positions for a user."""
        with self._session_scope() as session:
            result = session.execute(
                text(
                    "SELECT * FROM signal_observation_positions "
                    "WHERE user_id = :user_id ORDER BY converted_at DESC LIMIT :limit"
                ),
                {"user_id": user_id, "limit": limit},
            )
            return [dict(row._mapping) for row in result.fetchall()]

    _UPDATABLE_POSITION_COLS = frozenset({
        "symbol", "shares", "entry_price", "current_price", "stop_loss",
        "target_price", "source", "status", "notes", "updated_at",
    })

    def update_position(self, position_id: str, user_id: int, data: dict[str, Any]) -> bool:
        """Update position data."""
        data["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        allowed = {k: v for k, v in data.items() if k in self._UPDATABLE_POSITION_COLS}
        sets = ", ".join([f"{quote_identifier(k)} = :{k}" for k in allowed])
        with self._session_scope(commit=True) as session:
            session.execute(
                text(f"UPDATE signal_observation_positions SET {sets} WHERE id = :id AND user_id = :user_id"),
                {**allowed, "id": position_id, "user_id": user_id},
            )
        return True

    def get_stats(self, user_id: int) -> dict[str, Any]:
        """Get observation statistics by source."""
        with self._session_scope() as session:
            result = session.execute(
                text("""
                    SELECT source,
                           COUNT(*) as count,
                           SUM(CASE WHEN status = 'open' THEN 1 ELSE 0 END) as open_count,
                           SUM(CASE WHEN trigger_status = 'target_hit' THEN 1 ELSE 0 END) as target_hits,
                           SUM(CASE WHEN trigger_status = 'stop_hit' THEN 1 ELSE 0 END) as stop_hits,
                           AVG(return_pct) as avg_return_pct,
                           AVG(max_gain_pct) as avg_max_gain_pct,
                           AVG(max_drawdown_pct) as avg_max_drawdown_pct
                    FROM signal_observations
                    WHERE user_id = :user_id
                    GROUP BY source
                """),
                {"user_id": user_id},
            )

            items = []
            total = 0
            for row in result.fetchall():
                d = dict(row._mapping)
                count = d["count"] or 0
                total += count
                d["target_hit_rate"] = round(d["target_hits"] / count * 100, 2) if count else 0
                d["stop_hit_rate"] = round(d["stop_hits"] / count * 100, 2) if count else 0
                items.append(d)

        return {"items": items, "total": total}
