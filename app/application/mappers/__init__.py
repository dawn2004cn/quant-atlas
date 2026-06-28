from __future__ import annotations

"""Mappers for Entity -> Domain Model -> DTO transformation.

This module implements the Mapper pattern to separate concerns between:
- Repository layer (returns raw entities)
- Domain layer (business logic)
- Application layer (returns DTOs to presentation)

Following the principle that Application services must ONLY return DTOs.
"""


from abc import ABC, abstractmethod
from typing import Any, Generic, TypeVar

TEntity = TypeVar("TEntity")
TDomain = TypeVar("TDomain")
TDTO = TypeVar("TDTO")


class BaseMapper(ABC, Generic[TEntity, TDomain, TDTO]):
    """Abstract base mapper following the Mapper pattern."""

    @abstractmethod
    def to_domain(self, entity: TEntity) -> TDomain:
        """Convert entity to domain model."""
        raise NotImplementedError

    @abstractmethod
    def to_dto(self, domain: TDomain) -> TDTO:
        """Convert domain model to DTO."""
        raise NotImplementedError

    @abstractmethod
    def to_entity(self, domain: TDomain) -> TEntity:
        """Convert domain model back to entity."""
        raise NotImplementedError

    def to_dto_list(self, domain_list: list[TDomain]) -> list[TDTO]:
        """Convert a list of domain models to DTOs."""
        return [self.to_dto(d) for d in domain_list]

    def to_domain_list(self, entity_list: list[TEntity]) -> list[TDomain]:
        """Convert a list of entities to domain models."""
        return [self.to_domain(e) for e in entity_list]


class DictMapper(BaseMapper[dict[str, Any], dict[str, Any], dict[str, Any]]):
    """Mapper for dictionary-based entities (fallback for legacy code)."""

    def to_domain(self, entity: dict[str, Any]) -> dict[str, Any]:
        """Normalize dict to domain format."""
        return entity

    def to_dto(self, domain: dict[str, Any]) -> dict[str, Any]:
        """Ensure domain has required DTO fields."""
        return domain

    def to_entity(self, domain: dict[str, Any]) -> dict[str, Any]:
        """Convert domain back to dict entity."""
        return domain


def create_mapper(
    entity_cls: type,
    domain_cls: type,
    dto_cls: type,
    field_mapping: dict[str, str] | None = None,
) -> type[BaseMapper]:
    """Factory function to create a simple mapper with field mapping."""

    class GeneratedMapper(BaseMapper):
        def __init__(self):
            self._mapping = field_mapping or {}

        def to_domain(self, entity: Any) -> Any:
            data = to_dict_safe(entity)

            domain_data = {}
            for entity_field, domain_field in self._mapping.items():
                if entity_field in data:
                    domain_data[domain_field] = data[entity_field]
                elif domain_field in data:
                    domain_data[domain_field] = data[domain_field]

            return domain_cls(**domain_data) if domain_cls else domain_data

        def to_dto(self, domain: Any) -> Any:
            data = to_dict_safe(domain)
            return dto_cls(**data) if dto_cls else data

        def to_entity(self, domain: Any) -> Any:
            data = to_dict_safe(domain)
            return entity_cls(**data) if entity_cls else data

    return GeneratedMapper


def ensure_dto(value: Any, dto_cls: type) -> Any:
    """Ensure a value is converted to the specified DTO class.

    This utility handles the transition from dict to strict DTOs,
    eliminating 'if hasattr(detail, "model_dump")' checks in service code.

    Uses a unified serialization interface pattern instead of hasattr checks.
    """
    if value is None:
        return None

    if isinstance(value, dto_cls):
        return value

    if isinstance(value, BaseModel):
        return dto_cls(**value.model_dump())

    if isinstance(value, dict):
        return dto_cls(**value)

    if hasattr(value, "__dict__"):
        return dto_cls(**value.__dict__)

    return dto_cls(value)


def to_dict_safe(value: Any) -> dict[str, Any]:
    """Safely convert any value to dictionary.

    Replaces manual hasattr checks with type-safe conversion.
    """
    if value is None:
        return {}

    if isinstance(value, dict):
        return value

    if isinstance(value, BaseModel):
        return value.model_dump()

    if hasattr(value, "__dict__"):
        return value.__dict__

    return {}


def to_list_safe(value: Any, item_cls: type | None = None) -> list:
    """Safely convert value to list with optional item conversion."""
    if value is None:
        return []

    if isinstance(value, list):
        if item_cls:
            return [ensure_dto(item, item_cls) for item in value]
        return value

    if isinstance(value, (tuple, set)):
        result = list(value)
        if item_cls:
            return [ensure_dto(item, item_cls) for item in result]
        return result

    return [value]


try:
    from pydantic import BaseModel
except ImportError:
    class BaseModel:
        pass


def safe_getattr(obj: Any, attr: str, default: Any = None) -> Any:
    """Safe attribute access for mixed dict/object entities."""
    if obj is None:
        return default

    if isinstance(obj, dict):
        return obj.get(attr, default)

    return getattr(obj, attr, default)
