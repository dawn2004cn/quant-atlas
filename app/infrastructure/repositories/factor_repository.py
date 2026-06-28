from __future__ import annotations

"""Factor Repository - manages factor metadata and performance data.

This module provides CRUD operations for factor metadata, IC records,
exposures, and decay detection.
"""


from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import desc, select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.domain.ports.factor_repository_port import FactorRepositoryPort
from app.infrastructure.database.models.factor import (
    FactorDecayLog,
    FactorICRecord,
    FactorMetadata,
)


class FactorRepository(FactorRepositoryPort):
    """Repository for factor management."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession] | None = None):
        self._session_factory = session_factory

    async def create_factor(self, factor_data: dict[str, Any]) -> str:
        """Create a new factor with metadata."""
        if not self._session_factory:
            raise RuntimeError("Session factory not configured")

        async with self._session_factory() as session:
            factor = FactorMetadata(
                factor_id=factor_data.get("factor_id"),
                factor_name=factor_data.get("factor_name"),
                factor_expression=factor_data.get("factor_expression"),
                category=factor_data.get("category", "custom"),
                description=factor_data.get("description"),
                ic_mean=factor_data.get("ic_mean", 0.0),
                ic_std=factor_data.get("ic_std", 0.0),
                ir=factor_data.get("ir", 0.0),
                decay_rate=factor_data.get("decay_rate", 0.0),
                effective_date=factor_data.get("effective_date"),
                status=factor_data.get("status", "active"),
                owner=factor_data.get("owner", "system"),
            )
            session.add(factor)
            await session.commit()
            return factor.factor_id

    async def get_factor(self, factor_id: str) -> dict[str, Any] | None:
        """Get factor metadata by ID."""
        if not self._session_factory:
            return None

        async with self._session_factory() as session:
            result = await session.execute(
                select(FactorMetadata).where(FactorMetadata.factor_id == factor_id)
            )
            factor = result.scalars().first()
            if not factor:
                return None
            return self._factor_to_dict(factor)

    async def list_factors(
        self,
        category: str | None = None,
        status: str | None = None,
        order_by: str = "ic_mean",
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """List factors with optional filtering."""
        if not self._session_factory:
            return []

        async with self._session_factory() as session:
            stmt = select(FactorMetadata)

            if category:
                stmt = stmt.where(FactorMetadata.category == category)
            if status:
                stmt = stmt.where(FactorMetadata.status == status)

            if order_by == "ic_mean":
                stmt = stmt.order_by(desc(FactorMetadata.ic_mean))
            elif order_by == "ir":
                stmt = stmt.order_by(desc(FactorMetadata.ir))
            elif order_by == "updated":
                stmt = stmt.order_by(desc(FactorMetadata.updated_at))

            stmt = stmt.limit(limit)

            result = await session.execute(stmt)
            factors = result.scalars().all()
            return [self._factor_to_dict(f) for f in factors]

    async def update_factor_performance(
        self,
        factor_id: str,
        ic_mean: float,
        ic_std: float,
        ir: float,
        decay_rate: float = 0.0,
    ) -> bool:
        """Update factor performance metrics."""
        if not self._session_factory:
            return False

        async with self._session_factory() as session:
            stmt = (
                update(FactorMetadata)
                .where(FactorMetadata.factor_id == factor_id)
                .values(
                    ic_mean=ic_mean,
                    ic_std=ic_std,
                    ir=ir,
                    decay_rate=decay_rate,
                    last_calculated_at=datetime.now(),
                    updated_at=datetime.now(),
                )
            )
            result = await session.execute(stmt)
            await session.commit()
            return result.rowcount > 0

    async def deactivate_factor(self, factor_id: str, reason: str = "") -> bool:
        """Deactivate a factor (soft delete)."""
        if not self._session_factory:
            return False

        async with self._session_factory() as session:
            stmt = (
                update(FactorMetadata)
                .where(FactorMetadata.factor_id == factor_id)
                .values(
                    status="deprecated",
                    expiration_date=datetime.now().strftime("%Y-%m-%d"),
                    updated_at=datetime.now(),
                )
            )
            result = await session.execute(stmt)
            await session.commit()
            return result.rowcount > 0

    async def add_ic_record(
        self,
        factor_id: str,
        calc_date: str,
        ic_value: float,
        rank_ic: float | None = None,
        forward_return: float = 0.0,
        sample_count: int = 0,
    ) -> int:
        """Add an IC record for a factor."""
        if not self._session_factory:
            raise RuntimeError("Session factory not configured")

        async with self._session_factory() as session:
            record = FactorICRecord(
                factor_id=factor_id,
                calc_date=calc_date,
                ic_value=ic_value,
                rank_ic_value=rank_ic,
                forward_return=forward_return,
                sample_count=sample_count,
            )
            session.add(record)
            await session.commit()
            return record.id

    async def get_ic_history(
        self,
        factor_id: str,
        days: int = 60,
    ) -> list[dict[str, Any]]:
        """Get IC history for a factor."""
        if not self._session_factory:
            return []

        async with self._session_factory() as session:
            cutoff_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

            stmt = (
                select(FactorICRecord)
                .where(
                    FactorICRecord.factor_id == factor_id,
                    FactorICRecord.calc_date >= cutoff_date,
                )
                .order_by(FactorICRecord.calc_date)
            )

            result = await session.execute(stmt)
            records = result.scalars().all()

            return [
                {
                    "calc_date": r.calc_date,
                    "ic_value": r.ic_value,
                    "rank_ic_value": r.rank_ic_value,
                    "forward_return": r.forward_return,
                }
                for r in records
            ]

    async def get_top_factors(self, limit: int = 20, min_ir: float = 0.5) -> list[dict[str, Any]]:
        """Get top performing factors by IR."""
        if not self._session_factory:
            return []

        async with self._session_factory() as session:
            stmt = (
                select(FactorMetadata)
                .where(
                    FactorMetadata.status == "active",
                    FactorMetadata.ir >= min_ir,
                )
                .order_by(desc(FactorMetadata.ir))
                .limit(limit)
            )

            result = await session.execute(stmt)
            factors = result.scalars().all()
            return [self._factor_to_dict(f) for f in factors]

    async def log_decay_event(
        self,
        factor_id: str,
        detection_date: str,
        ic_mean_current: float,
        ic_mean_historical: float,
        decay_ratio: float,
        severity: str = "normal",
    ) -> int:
        """Log a factor decay detection event."""
        if not self._session_factory:
            raise RuntimeError("Session factory not configured")

        async with self._session_factory() as session:
            log = FactorDecayLog(
                factor_id=factor_id,
                detection_date=detection_date,
                ic_mean_current=ic_mean_current,
                ic_mean_historical=ic_mean_historical,
                decay_ratio=decay_ratio,
                severity=severity,
            )
            session.add(log)
            await session.commit()
            return log.id

    def _factor_to_dict(self, factor: FactorMetadata) -> dict[str, Any]:
        """Convert FactorMetadata to dictionary."""
        return {
            "factor_id": factor.factor_id,
            "factor_name": factor.factor_name,
            "factor_expression": factor.factor_expression,
            "category": factor.category,
            "description": factor.description,
            "ic_mean": factor.ic_mean,
            "ic_std": factor.ic_std,
            "ir": factor.ir,
            "ic_t_stat": factor.ic_t_stat,
            "win_rate": factor.win_rate,
            "decay_rate": factor.decay_rate,
            "half_life_days": factor.half_life_days,
            "turnover_rate": factor.turnover_rate,
            "effective_date": factor.effective_date,
            "expiration_date": factor.expiration_date,
            "status": factor.status,
            "version": factor.version,
            "owner": factor.owner,
            "tags": factor.tags,
            "sample_count": factor.sample_count,
            "last_calculated_at": factor.last_calculated_at.isoformat() if factor.last_calculated_at else None,
            "created_at": factor.created_at.isoformat() if factor.created_at else None,
        }


class SyncFactorRepository:
    """Synchronous version of FactorRepository for legacy code."""

    def __init__(self, session_factory=None):
        self._session_factory = session_factory

    def create_factor(self, factor_data: dict[str, Any]) -> str:
        """Create a new factor (sync version)."""
        if not self._session_factory:
            raise RuntimeError("Session factory not configured")

        session = self._session_factory()
        try:
            factor = FactorMetadata(
                factor_id=factor_data.get("factor_id"),
                factor_name=factor_data.get("factor_name"),
                factor_expression=factor_data.get("factor_expression"),
                category=factor_data.get("category", "custom"),
                ic_mean=factor_data.get("ic_mean", 0.0),
                ic_std=factor_data.get("ic_std", 0.0),
                ir=factor_data.get("ir", 0.0),
            )
            session.add(factor)
            session.commit()
            return factor.factor_id
        finally:
            session.close()
            if hasattr(self._session_factory, "remove"):
                self._session_factory.remove()

    def list_factors(self, status: str = "active", limit: int = 100) -> list[dict]:
        """List factors (sync version)."""
        if not self._session_factory:
            return []

        session = self._session_factory()
        try:
            stmt = (
                select(FactorMetadata)
                .where(FactorMetadata.status == status)
                .order_by(desc(FactorMetadata.ir))
                .limit(limit)
            )
            result = session.execute(stmt)
            factors = result.scalars().all()
            return [
                {
                    "factor_id": f.factor_id,
                    "factor_name": f.factor_name,
                    "ic_mean": f.ic_mean,
                    "ir": f.ir,
                    "status": f.status,
                }
                for f in factors
            ]
        finally:
            session.close()
            if hasattr(self._session_factory, "remove"):
                self._session_factory.remove()


__all__ = ["FactorRepository", "SyncFactorRepository"]
