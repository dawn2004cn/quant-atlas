from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Column, DateTime, Integer, MetaData, Numeric, String, Table, Text, select, update

from app.domain.sniper_entities import MarketRegime, SniperSelection


class MySQLSniperRepository:
    def __init__(self, session_factory):
        self._session_factory = session_factory
        self._metadata = MetaData()
        self._table = Table(
            "sniper_selections",
            self._metadata,
            Column("id", Integer, primary_key=True),
            Column("symbol", String(20)),
            Column("name", String(50)),
            Column("strategy_name", String(50)),
            Column("regime", String(20)),
            Column("commander_reason", Text),
            Column("agent_consensus", JSON),
            Column("initial_price", Numeric(10, 2)),
            Column("current_price", Numeric(10, 2)),
            Column("shares", Integer),
            Column("stop_loss", Numeric(10, 2)),
            Column("take_profit", Numeric(10, 2)),
            Column("status", String(20)),
            Column("pnl_amount", Numeric(15, 2)),
            Column("pnl_pct", Numeric(10, 2)),
            Column("selected_at", DateTime),
            Column("updated_at", DateTime),
        )

    def save(self, selection: SniperSelection) -> int:
        with self._session_factory() as session:
            data = {
                "symbol": selection.symbol,
                "name": selection.name,
                "strategy_name": selection.strategy_name,
                "regime": selection.regime.value,
                "commander_reason": selection.commander_reason,
                "agent_consensus": selection.agent_consensus,
                "initial_price": selection.initial_price,
                "current_price": selection.current_price,
                "shares": selection.shares,
                "stop_loss": selection.stop_loss,
                "take_profit": selection.take_profit,
                "status": selection.status,
                "selected_at": datetime.now(),
            }
            result = session.execute(self._table.insert().values(**data))
            session.commit()
            return result.inserted_primary_key[0]

    def list_active(self) -> list[SniperSelection]:
        with self._session_factory() as session:
            stmt = select(self._table).where(self._table.c.status == "holding")
            rows = session.execute(stmt).fetchall()
            return [self._row_to_entity(row) for row in rows]

    def get_selection_summary(self, selection_id: int) -> dict[str, Any] | None:
        with self._session_factory() as session:
            stmt = select(self._table).where(self._table.c.id == selection_id)
            row = session.execute(stmt).fetchone()
            if not row:
                return None
            entity = self._row_to_entity(row)
            return {
                "symbol": entity.symbol,
                "name": entity.name,
                "commander_reason": entity.commander_reason,
                "agent_consensus": entity.agent_consensus,
            }

    def update_status(self, id: int, current_price: float, status: str, pnl_amount: float, pnl_pct: float):
        with self._session_factory() as session:
            stmt = update(self._table).where(self._table.c.id == id).values(
                current_price=current_price,
                status=status,
                pnl_amount=pnl_amount,
                pnl_pct=pnl_pct,
                updated_at=datetime.now()
            )
            session.execute(stmt)
            session.commit()

    def _row_to_entity(self, row) -> SniperSelection:
        return SniperSelection(
            id=row.id,
            symbol=row.symbol,
            name=row.name,
            strategy_name=row.strategy_name,
            regime=MarketRegime(row.regime),
            commander_reason=row.commander_reason,
            agent_consensus=row.agent_consensus if isinstance(row.agent_consensus, dict) else json.loads(row.agent_consensus or "{}"),
            initial_price=float(row.initial_price),
            current_price=float(row.current_price),
            shares=row.shares,
            stop_loss=float(row.stop_loss),
            take_profit=float(row.take_profit),
            status=row.status,
            pnl_amount=float(row.pnl_amount),
            pnl_pct=float(row.pnl_pct),
            selected_at=row.selected_at,
            updated_at=row.updated_at
        )
