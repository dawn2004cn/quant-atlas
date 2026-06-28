from __future__ import annotations
"""Execution Feedback Repository and Analysis Service.

Phase 42: 交易反馈环与滑点分析

This module provides:
- Repository for storing execution records
- Slippage analysis and statistics calculation
- Backtest parameter adjustment recommendations
"""


import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy import select, func

from app.infrastructure.database.models.execution_feedback import (
    ExecutionRecord,
    BacktestAdjustment,
)

logger = logging.getLogger(__name__)


class ExecutionFeedbackRepository:
    """Repository for execution feedback data."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession] | None = None):
        self._session_factory = session_factory

    async def record_execution(self, data: dict[str, Any]) -> int:
        """Record a single execution event."""
        if not self._session_factory:
            raise RuntimeError("Session factory not configured")

        async with self._session_factory() as session:
            record = ExecutionRecord(
                order_id=data["order_id"],
                strategy_id=data.get("strategy_id"),
                symbol=data["symbol"],
                side=data["side"],
                expected_price=data["expected_price"],
                fill_price=data["fill_price"],
                slippage=data.get("slippage", data["fill_price"] - data["expected_price"]),
                slippage_pct=data.get("slippage_pct", 0.0),
                expected_volume=data["expected_volume"],
                fill_volume=data.get("fill_volume", data["expected_volume"]),
                fill_rate=data.get("fill_rate", 1.0),
                order_time=data["order_time"],
                fill_time=data.get("fill_time"),
                latency_ms=data.get("latency_ms"),
                market_price_at_order=data.get("market_price_at_order"),
                spread_at_order=data.get("spread_at_order"),
                volatility_at_order=data.get("volatility_at_order"),
                execution_quality=data.get("execution_quality", "normal"),
                reason_code=data.get("reason_code"),
                gateway=data.get("gateway", "qmt"),
            )
            session.add(record)
            await session.commit()
            return record.id

    async def get_executions(
        self,
        symbol: str | None = None,
        strategy_id: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        limit: int = 1000,
    ) -> list[dict[str, Any]]:
        """Get execution records with optional filters."""
        if not self._session_factory:
            return []

        async with self._session_factory() as session:
            stmt = select(ExecutionRecord)

            if symbol:
                stmt = stmt.where(ExecutionRecord.symbol == symbol)
            if strategy_id:
                stmt = stmt.where(ExecutionRecord.strategy_id == strategy_id)
            if start_date:
                stmt = stmt.where(ExecutionRecord.order_time >= start_date)
            if end_date:
                stmt = stmt.where(ExecutionRecord.order_time <= end_date)

            stmt = stmt.order_by(ExecutionRecord.order_time.desc()).limit(limit)

            result = await session.execute(stmt)
            records = result.scalars().all()

            return [
                {
                    "order_id": r.order_id,
                    "symbol": r.symbol,
                    "side": r.side,
                    "expected_price": r.expected_price,
                    "fill_price": r.fill_price,
                    "slippage": r.slippage,
                    "slippage_pct": r.slippage_pct,
                    "latency_ms": r.latency_ms,
                    "execution_quality": r.execution_quality,
                    "order_time": r.order_time.isoformat() if r.order_time else None,
                    "fill_time": r.fill_time.isoformat() if r.fill_time else None,
                }
                for r in records
            ]

    async def calculate_slippage_stats(
        self,
        symbol: str | None = None,
        strategy_id: str | None = None,
        period: str = "daily",
    ) -> dict[str, Any]:
        """Calculate slippage statistics for a given period."""
        if not self._session_factory:
            return {}

        async with self._session_factory() as session:
            stmt = select(
                func.count(ExecutionRecord.id).label("total_orders"),
                func.avg(ExecutionRecord.slippage).label("avg_slippage"),
                func.avg(ExecutionRecord.slippage_pct).label("avg_slippage_pct"),
                func.max(ExecutionRecord.slippage).label("max_slippage"),
                func.min(ExecutionRecord.slippage).label("min_slippage"),
                func.avg(ExecutionRecord.latency_ms).label("avg_latency_ms"),
                func.max(ExecutionRecord.latency_ms).label("max_latency_ms"),
            )

            if symbol:
                stmt = stmt.where(ExecutionRecord.symbol == symbol)
            if strategy_id:
                stmt = stmt.where(ExecutionRecord.strategy_id == strategy_id)

            result = await session.execute(stmt)
            row = result.first()

            if not row:
                return {}

            return {
                "total_orders": row.total_orders or 0,
                "avg_slippage": float(row.avg_slippage or 0),
                "avg_slippage_pct": float(row.avg_slippage_pct or 0),
                "max_slippage": float(row.max_slippage or 0),
                "min_slippage": float(row.min_slippage or 0),
                "avg_latency_ms": float(row.avg_latency_ms or 0),
                "max_latency_ms": float(row.max_latency_ms or 0),
            }

    async def get_backtest_adjustments(
        self,
        strategy_id: str,
    ) -> list[dict[str, Any]]:
        """Get backtest parameter adjustments for a strategy."""
        if not self._session_factory:
            return []

        async with self._session_factory() as session:
            stmt = (
                select(BacktestAdjustment)
                .where(BacktestAdjustment.strategy_id == strategy_id)
                .order_by(BacktestAdjustment.created_at.desc())
            )

            result = await session.execute(stmt)
            adjustments = result.scalars().all()

            return [
                {
                    "id": a.id,
                    "original_slippage_model": a.original_slippage_model,
                    "original_slippage_value": a.original_slippage_value,
                    "adjusted_slippage_model": a.adjusted_slippage_model,
                    "adjusted_slippage_value": a.adjusted_slippage_value,
                    "adjustment_reason": a.adjustment_reason,
                    "applied": a.applied,
                }
                for a in adjustments
            ]

    async def save_backtest_adjustment(self, data: dict[str, Any]) -> int:
        """Save a backtest parameter adjustment."""
        if not self._session_factory:
            raise RuntimeError("Session factory not configured")

        async with self._session_factory() as session:
            adjustment = BacktestAdjustment(
                strategy_id=data["strategy_id"],
                original_slippage_model=data.get("original_slippage_model", "fixed"),
                original_slippage_value=data.get("original_slippage_value", 0.0),
                adjusted_slippage_model=data.get("adjusted_slippage_model", "dynamic"),
                adjusted_slippage_value=data.get("adjusted_slippage_value", 0.0),
                adjustment_reason=data.get("adjustment_reason", ""),
                original_backtest_return=data.get("original_backtest_return"),
                adjusted_backtest_return=data.get("adjusted_backtest_return"),
                return_difference=data.get("return_difference"),
            )
            session.add(adjustment)
            await session.commit()
            return adjustment.id


class SlippageAnalysisService:
    """Service for analyzing slippage and providing feedback."""

    def __init__(self, repository: ExecutionFeedbackRepository):
        self._repo = repository

    async def analyze_slippage(
        self,
        symbol: str | None = None,
        strategy_id: str | None = None,
        lookback_days: int = 30,
    ) -> dict[str, Any]:
        """Analyze slippage patterns and provide recommendations."""
        stats = await self._repo.calculate_slippage_stats(
            symbol=symbol,
            strategy_id=strategy_id,
        )

        if not stats:
            return {"status": "no_data"}

        # Determine execution quality
        avg_slippage_pct = abs(stats["avg_slippage_pct"])
        if avg_slippage_pct < 0.1:
            quality = "excellent"
        elif avg_slippage_pct < 0.5:
            quality = "good"
        elif avg_slippage_pct < 1.0:
            quality = "normal"
        else:
            quality = "poor"

        # Calculate recommended slippage for backtest
        recommended_slippage = stats["avg_slippage_pct"] * 1.2  # 20% buffer

        return {
            "status": "analyzed",
            "quality": quality,
            "stats": stats,
            "recommendations": {
                "backtest_slippage_pct": recommended_slippage,
                "backtest_slippage_model": "dynamic",
                "notes": self._generate_notes(stats, quality),
            },
        }

    def _generate_notes(self, stats: dict, quality: str) -> str:
        """Generate analysis notes based on statistics."""
        notes = []

        if stats["avg_latency_ms"] and stats["avg_latency_ms"] > 1000:
            notes.append(f"High latency detected: {stats['avg_latency_ms']:.0f}ms avg")

        if stats["max_slippage"] and stats["max_slippage"] > stats["avg_slippage"] * 3:
            notes.append("High slippage variance detected - consider limit orders")

        if quality == "poor":
            notes.append("Slippage is significantly impacting returns - review execution strategy")

        return "; ".join(notes) if notes else "Execution quality is within normal parameters"

    async def recommend_backtest_adjustment(
        self,
        strategy_id: str,
        current_slippage_model: str = "fixed",
        current_slippage_value: float = 0.0,
    ) -> dict[str, Any]:
        """Recommend backtest parameter adjustments based on real execution data."""
        analysis = await self.analyze_slippage(strategy_id=strategy_id)

        if analysis.get("status") != "analyzed":
            return {"status": "no_data", "recommendation": None}

        recommendations = analysis["recommendations"]

        adjustment = {
            "strategy_id": strategy_id,
            "original_slippage_model": current_slippage_model,
            "original_slippage_value": current_slippage_value,
            "adjusted_slippage_model": recommendations["backtest_slippage_model"],
            "adjusted_slippage_value": recommendations["backtest_slippage_pct"],
            "adjustment_reason": f"Based on {analysis['stats']['total_orders']} real executions over lookback period",
        }

        return {
            "status": "recommendation_ready",
            "adjustment": adjustment,
            "analysis": analysis,
        }


__all__ = [
    "ExecutionFeedbackRepository",
    "SlippageAnalysisService",
]
