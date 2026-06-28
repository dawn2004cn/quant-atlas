from __future__ import annotations

"""SQLAlchemy implementation of QuantMLFactorRepository."""


import json
from typing import Any

from sqlalchemy import delete, select

from app.domain.ports import QuantMLFactorRepository
from app.domain.quantml_entities import QuantMLFactor
from app.infrastructure.database.models.advanced import QuantMLFactor as DBQuantMLFactor


class MySQLQuantMLFactorRepository(QuantMLFactorRepository):
    def __init__(self, session_factory):
        self._session_factory = session_factory

    def save_factor(self, factor: Any) -> str:
        """Save factor (stub for interface compatibility)."""
        if hasattr(factor, 'factor_name'):
            return str(factor.factor_name)
        return "stub_factor_id"

    def get_factor(self, factor_id: str) -> Any | None:
        """Get factor (stub for interface compatibility)."""
        return None

    def save_real_factor(self, factor: QuantMLFactor) -> int:
        session = self._session_factory()
        try:
            db_factor = DBQuantMLFactor(
                factor_name=factor.factor_name,
                category=factor.category,
                ic_mean=factor.ic_mean,
                icir=factor.icir,
                long_average=factor.long_average,
                long_short=factor.long_short,
                t_stat=factor.t_stat,
                metadata_json=json.dumps(factor.metadata)
            )
            session.add(db_factor)
            session.commit()
            factor.id = db_factor.id
            return factor.id
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def clear_all(self) -> None:
        session = self._session_factory()
        try:
            session.execute(delete(DBQuantMLFactor))
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def list_factors(self, category: str | None = None, limit: int = 100) -> list[QuantMLFactor]:
        session = self._session_factory()
        try:
            stmt = select(DBQuantMLFactor)
            if category:
                stmt = stmt.where(DBQuantMLFactor.category == category)
            stmt = stmt.limit(limit)
            rows = session.scalars(stmt).all()
            return [self._map_db_to_factor(r) for r in rows]
        finally:
            session.close()

    def _map_db_to_factor(self, r: DBQuantMLFactor) -> QuantMLFactor:
        return QuantMLFactor(
            id=r.id,
            factor_name=r.factor_name,
            category=r.category,
            ic_mean=r.ic_mean,
            icir=r.icir,
            long_average=r.long_average,
            long_short=r.long_short,
            t_stat=r.t_stat,
            metadata=json.loads(r.metadata_json) if r.metadata_json else {},
            created_at=r.created_at
        )
