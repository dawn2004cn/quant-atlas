from __future__ import annotations
"""MySQL repository for AI committee selection runs and simulated trades."""


import json
from typing import Any

from datetime import datetime

from sqlalchemy import select

from app.infrastructure.database.models.advanced import (
    AICommitteeSelectionRun,
    AICommitteeSelectionTrade,
)


class MySQLAICommitteeSelectionRepository:
    """Persist committee selection runs and simulated trades."""

    def __init__(self, session_factory):
        self._session_factory = session_factory

    def save_run(self, payload: dict[str, Any]) -> None:
        session = self._session_factory()
        try:
            run = AICommitteeSelectionRun(
                id=payload["id"],
                user_id=payload.get("user_id"),
                status=payload.get("status", "completed"),
                capital=float(payload.get("capital") or 500000),
                market_regime=payload.get("overall_regime", "sideways"),
                risk_level=payload.get("risk_level", "medium"),
                selected_count=len(payload.get("selected_stocks") or []),
                agents_json=json.dumps(payload.get("agents") or [], ensure_ascii=False),
                indexes_json=json.dumps(payload.get("indexes") or [], ensure_ascii=False),
                strategies_json=json.dumps(payload.get("strategy_array") or [], ensure_ascii=False),
                reasoning=payload.get("reasoning") or "",
            )
            session.merge(run)
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def save_trades(self, run_id: str, user_id: int | None, trades: list[dict[str, Any]]) -> None:
        session = self._session_factory()
        try:
            for item in trades:
                session.add(
                    AICommitteeSelectionTrade(
                        run_id=run_id,
                        user_id=user_id,
                        symbol=item.get("symbol") or "",
                        name=item.get("name") or "",
                        strategy_id=item.get("strategy_id") or "",
                        strategy_name=item.get("strategy") or item.get("strategy_name") or "",
                        side=item.get("side") or "BUY",
                        status=item.get("status") or "open",
                        entry_price=float(item.get("entry_price") or 0),
                        current_price=float(item.get("current_price") or item.get("entry_price") or 0),
                        quantity=int(item.get("quantity") or 0),
                        capital_used=float(item.get("capital_used") or 0),
                        stop_loss=float(item.get("stop_loss") or 0),
                        take_profit=float(item.get("take_profit") or 0),
                        pnl_pct=float(item.get("pnl_pct") or 0),
                        sniper_score=float(item.get("sniper_score") or 0),
                        rationale=item.get("rationale") or "",
                    )
                )
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def list_runs(self, user_id: int | None = None, limit: int = 20) -> list[dict[str, Any]]:
        session = self._session_factory()
        try:
            stmt = select(AICommitteeSelectionRun).order_by(AICommitteeSelectionRun.created_at.desc()).limit(limit)
            if user_id is not None:
                stmt = stmt.where(AICommitteeSelectionRun.user_id == user_id)
            return [self._run_to_dict(row) for row in session.scalars(stmt).all()]
        finally:
            session.close()

    def list_trades(self, user_id: int | None = None, only_open: bool = False, limit: int = 100) -> list[dict[str, Any]]:
        session = self._session_factory()
        try:
            stmt = select(AICommitteeSelectionTrade).order_by(AICommitteeSelectionTrade.opened_at.desc()).limit(limit)
            if user_id is not None:
                stmt = stmt.where(AICommitteeSelectionTrade.user_id == user_id)
            if only_open:
                stmt = stmt.where(AICommitteeSelectionTrade.status == "open")
            return [self._trade_to_dict(row) for row in session.scalars(stmt).all()]
        finally:
            session.close()

    def update_trade_tracking(self, trade_id: int, current_price: float, status: str, pnl_pct: float) -> None:
        session = self._session_factory()
        try:
            row = session.get(AICommitteeSelectionTrade, trade_id)
            if row is None:
                return
            row.current_price = current_price
            row.status = status
            row.pnl_pct = pnl_pct
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def _run_to_dict(self, row: AICommitteeSelectionRun) -> dict[str, Any]:
        return {
            "id": row.id,
            "status": row.status,
            "capital": row.capital,
            "overall_regime": row.market_regime,
            "risk_level": row.risk_level,
            "selected_count": row.selected_count,
            "created_at": row.created_at.isoformat() if row.created_at else None,
        }

    def _trade_to_dict(self, row: AICommitteeSelectionTrade) -> dict[str, Any]:
        return {
            "id": row.id,
            "run_id": row.run_id,
            "symbol": row.symbol,
            "name": row.name,
            "strategy_id": row.strategy_id,
            "strategy": row.strategy_name,
            "side": row.side,
            "status": row.status,
            "entry_price": row.entry_price,
            "current_price": row.current_price,
            "quantity": row.quantity,
            "capital_used": row.capital_used,
            "stop_loss": row.stop_loss,
            "take_profit": row.take_profit,
            "pnl_pct": row.pnl_pct,
            "sniper_score": row.sniper_score,
            "rationale": row.rationale,
            "opened_at": row.opened_at.isoformat() if row.opened_at else None,
            "updated_at": row.updated_at.isoformat() if row.updated_at else None,
        }
