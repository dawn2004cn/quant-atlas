from __future__ import annotations
"""SQLAlchemy OpenBB repository implementation."""


import json
from datetime import datetime, timedelta
from typing import Any
from sqlalchemy import select, and_

from app.domain.ports import OpenBBRepository
from app.domain.market_entities import ProviderConfig
from app.infrastructure.database.models.advanced import OpenBBProviderConfig, OpenBBDataCache


class MySQLOpenBBRepository(OpenBBRepository):
    def __init__(self, session_factory):
        self._session_factory = session_factory

    def save_data(self, key: str, data: Any) -> bool:
        """Save data to cache (stub for interface compatibility)."""
        return True

    def get_data(self, key: str) -> Any | None:
        """Get cached data (stub for interface compatibility)."""
        return None

    def get_provider_config(self, provider_name: str) -> ProviderConfig | None:
        session = self._session_factory()
        try:
            db_config = session.get(OpenBBProviderConfig, provider_name)
            if not db_config:
                return None
            return ProviderConfig(
                provider_name=db_config.provider_name,
                is_enabled=bool(db_config.is_enabled),
                settings=json.loads(db_config.settings_json) if db_config.settings_json else {},
                updated_at=db_config.updated_at
            )
        finally:
            session.close()

    def save_provider_config(self, config: ProviderConfig) -> None:
        session = self._session_factory()
        try:
            db_config = session.get(OpenBBProviderConfig, config.provider_name)
            if not db_config:
                db_config = OpenBBProviderConfig(provider_name=config.provider_name)
                session.add(db_config)

            db_config.is_enabled = 1 if config.is_enabled else 0
            db_config.settings_json = json.dumps(config.settings)
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def get_cached_data(self, provider: str, symbol: str, data_type: str, timeframe: str | None = None) -> Any:
        session = self._session_factory()
        try:
            stmt = select(OpenBBDataCache).where(
                and_(
                    OpenBBDataCache.provider == provider,
                    OpenBBDataCache.symbol == symbol,
                    OpenBBDataCache.data_type == data_type,
                    OpenBBDataCache.timeframe == timeframe,
                    (OpenBBDataCache.expires_at > datetime.now())
                )
            )
            db_cache = session.scalars(stmt).first()
            if db_cache:
                return json.loads(db_cache.payload_json)
            return None
        finally:
            session.close()

    def cache_data(self, provider: str, symbol: str, data_type: str, payload: Any, timeframe: str | None = None, ttl_hours: int = 24) -> None:
        session = self._session_factory()
        try:
            db_cache = OpenBBDataCache(
                provider=provider,
                symbol=symbol,
                data_type=data_type,
                timeframe=timeframe,
                payload_json=json.dumps(payload),
                expires_at=datetime.now() + timedelta(hours=ttl_hours)
            )
            session.add(db_cache)
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
