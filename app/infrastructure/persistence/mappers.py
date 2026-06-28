from __future__ import annotations

"""Persistence mappers - Entity to DBModel mapping layer."""


from datetime import datetime
from typing import Any

from app.core.logger import get_logger

logger = get_logger(__name__)


class EntityMapper:
    """Base mapper interface."""

    @staticmethod
    def to_entity(db_model: Any) -> Any:
        """Convert DB model to domain entity."""
        raise NotImplementedError

    @staticmethod
    def to_db_model(entity: Any) -> Any:
        """Convert domain entity to DB model."""
        raise NotImplementedError


class StockMapper(EntityMapper):
    """Mapper for Stock entity."""

    @staticmethod
    def to_entity(db_model: dict | Any) -> dict | None:
        """Convert DB model to Stock entity."""
        if db_model is None:
            return None

        if hasattr(db_model, '__dict__'):
            db_model = db_model.__dict__

        return {
            "code": db_model.get("code", ""),
            "name": db_model.get("name", ""),
            "market": db_model.get("market", "CN"),
            "industry": db_model.get("industry", ""),
            "sector": db_model.get("sector", ""),
            "created_at": db_model.get("created_at"),
            "updated_at": db_model.get("updated_at"),
        }

    @staticmethod
    def to_db_model(entity: dict) -> dict:
        """Convert Stock entity to DB model."""
        return {
            "code": entity.get("code"),
            "name": entity.get("name", ""),
            "market": entity.get("market", "CN"),
            "industry": entity.get("industry", ""),
            "sector": entity.get("sector", ""),
            "created_at": entity.get("created_at") or datetime.now(),
            "updated_at": datetime.now(),
        }


class QuoteMapper(EntityMapper):
    """Mapper for Quote entity."""

    @staticmethod
    def to_entity(db_model: dict | Any) -> dict | None:
        """Convert DB model to Quote entity."""
        if db_model is None:
            return None

        if hasattr(db_model, '__dict__'):
            db_model = db_model.__dict__

        return {
            "code": db_model.get("code", ""),
            "name": db_model.get("name", ""),
            "price": db_model.get("price", 0.0),
            "change": db_model.get("change", 0.0),
            "change_pct": db_model.get("change_pct", 0.0),
            "volume": db_model.get("volume", 0),
            "amount": db_model.get("amount", 0.0),
            "high": db_model.get("high", 0.0),
            "low": db_model.get("low", 0.0),
            "open": db_model.get("open", 0.0),
            "prev_close": db_model.get("prev_close", 0.0),
            "bid": db_model.get("bid", 0.0),
            "ask": db_model.get("ask", 0.0),
            "timestamp": db_model.get("timestamp") or datetime.now(),
        }

    @staticmethod
    def to_db_model(entity: dict) -> dict:
        """Convert Quote entity to DB model."""
        return {
            "code": entity.get("code"),
            "price": entity.get("price", 0.0),
            "change": entity.get("change", 0.0),
            "change_pct": entity.get("change_pct", 0.0),
            "volume": entity.get("volume", 0),
            "amount": entity.get("amount", 0.0),
            "high": entity.get("high", 0.0),
            "low": entity.get("low", 0.0),
            "open": entity.get("open", 0.0),
            "prev_close": entity.get("prev_close", 0.0),
            "bid": entity.get("bid", 0.0),
            "ask": entity.get("ask", 0.0),
            "updated_at": datetime.now(),
        }


class UserMapper(EntityMapper):
    """Mapper for User entity."""

    @staticmethod
    def to_entity(db_model: dict | Any) -> dict | None:
        """Convert DB model to User entity."""
        if db_model is None:
            return None

        if hasattr(db_model, '__dict__'):
            db_model = db_model.__dict__

        return {
            "id": str(db_model.get("id", "")),
            "username": db_model.get("username", ""),
            "email": db_model.get("email", ""),
            "is_active": db_model.get("is_active", True),
            "created_at": db_model.get("created_at"),
            "updated_at": db_model.get("updated_at"),
        }

    @staticmethod
    def to_db_model(entity: dict) -> dict:
        """Convert User entity to DB model."""
        return {
            "username": entity.get("username"),
            "email": entity.get("email", ""),
            "password_hash": entity.get("password_hash", ""),
            "is_active": entity.get("is_active", True),
            "created_at": entity.get("created_at") or datetime.now(),
        }


class WatchlistMapper(EntityMapper):
    """Mapper for Watchlist entity."""

    @staticmethod
    def to_entity(db_model: dict | Any) -> dict | None:
        """Convert DB model to Watchlist entity."""
        if db_model is None:
            return None

        if hasattr(db_model, '__dict__'):
            db_model = db_model.__dict__

        return {
            "id": db_model.get("id", 0),
            "user_id": db_model.get("user_id", ""),
            "name": db_model.get("name", ""),
            "description": db_model.get("description", ""),
            "color": db_model.get("color", ""),
            "is_default": db_model.get("is_default", False),
            "created_at": db_model.get("created_at"),
            "updated_at": db_model.get("updated_at"),
        }

    @staticmethod
    def to_db_model(entity: dict) -> dict:
        """Convert Watchlist entity to DB model."""
        return {
            "user_id": entity.get("user_id"),
            "name": entity.get("name"),
            "description": entity.get("description", ""),
            "color": entity.get("color", ""),
            "is_default": entity.get("is_default", False),
            "created_at": entity.get("created_at") or datetime.now(),
        }


class PositionMapper(EntityMapper):
    """Mapper for Position entity."""

    @staticmethod
    def to_entity(db_model: dict | Any) -> dict | None:
        """Convert DB model to Position entity."""
        if db_model is None:
            return None

        if hasattr(db_model, '__dict__'):
            db_model = db_model.__dict__

        return {
            "id": str(db_model.get("id", "")),
            "user_id": db_model.get("user_id", ""),
            "code": db_model.get("code", ""),
            "name": db_model.get("name", ""),
            "side": db_model.get("side", "long"),
            "quantity": db_model.get("quantity", 0),
            "avg_cost": db_model.get("avg_cost", 0.0),
            "current_price": db_model.get("current_price", 0.0),
            "opened_at": db_model.get("opened_at"),
            "closed_at": db_model.get("closed_at"),
            "status": db_model.get("status", "open"),
        }

    @staticmethod
    def to_db_model(entity: dict) -> dict:
        """Convert Position entity to DB model."""
        return {
            "user_id": entity.get("user_id"),
            "code": entity.get("code"),
            "name": entity.get("name", ""),
            "side": entity.get("side", "long"),
            "quantity": entity.get("quantity", 0),
            "avg_cost": entity.get("avg_cost", 0.0),
            "current_price": entity.get("current_price", 0.0),
            "opened_at": entity.get("opened_at") or datetime.now(),
            "status": entity.get("status", "open"),
        }


class SignalMapper(EntityMapper):
    """Mapper for Signal entity."""

    @staticmethod
    def to_entity(db_model: dict | Any) -> dict | None:
        """Convert DB model to Signal entity."""
        if db_model is None:
            return None

        if hasattr(db_model, '__dict__'):
            db_model = db_model.__dict__

        return {
            "id": str(db_model.get("id", "")),
            "code": db_model.get("code", ""),
            "name": db_model.get("name", ""),
            "signal_type": db_model.get("signal_type", ""),
            "direction": db_model.get("direction", "long"),
            "strength": db_model.get("strength", "moderate"),
            "price": db_model.get("price", 0.0),
            "target_price": db_model.get("target_price"),
            "stop_loss": db_model.get("stop_loss"),
            "confidence": db_model.get("confidence", 50.0),
            "reason": db_model.get("reason", ""),
            "generated_at": db_model.get("generated_at") or datetime.now(),
            "expires_at": db_model.get("expires_at"),
        }

    @staticmethod
    def to_db_model(entity: dict) -> dict:
        """Convert Signal entity to DB model."""
        return {
            "code": entity.get("code"),
            "name": entity.get("name", ""),
            "signal_type": entity.get("signal_type"),
            "direction": entity.get("direction", "long"),
            "strength": entity.get("strength", "moderate"),
            "price": entity.get("price", 0.0),
            "target_price": entity.get("target_price"),
            "stop_loss": entity.get("stop_loss"),
            "confidence": entity.get("confidence", 50.0),
            "reason": entity.get("reason", ""),
            "generated_at": entity.get("generated_at") or datetime.now(),
            "expires_at": entity.get("expires_at"),
        }


class MapperRegistry:
    """Registry for all entity mappers."""

    _mappers = {
        "stock": StockMapper,
        "quote": QuoteMapper,
        "user": UserMapper,
        "watchlist": WatchlistMapper,
        "position": PositionMapper,
        "signal": SignalMapper,
    }

    @classmethod
    def get_mapper(cls, entity_type: str) -> EntityMapper | None:
        """Get mapper for entity type."""
        mapper_class = cls._mappers.get(entity_type.lower())
        if mapper_class:
            return mapper_class()
        logger.warning(f"No mapper found for entity type: {entity_type}")
        return None

    @classmethod
    def to_entity(cls, entity_type: str, db_model: Any) -> Any:
        """Convert DB model to entity."""
        mapper = cls.get_mapper(entity_type)
        if mapper:
            return mapper.to_entity(db_model)
        return db_model

    @classmethod
    def to_db_model(cls, entity_type: str, entity: dict) -> dict:
        """Convert entity to DB model."""
        mapper = cls.get_mapper(entity_type)
        if mapper:
            return mapper.to_db_model(entity)
        return entity


__all__ = [
    "EntityMapper",
    "StockMapper",
    "QuoteMapper",
    "UserMapper",
    "WatchlistMapper",
    "PositionMapper",
    "SignalMapper",
    "MapperRegistry",
]
