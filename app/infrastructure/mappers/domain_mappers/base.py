from __future__ import annotations
"""Data Mapper for converting ORM Models to Domain Entities."""

from typing import TypeVar, Generic

T_Entity = TypeVar("T_Entity")
T_Model = TypeVar("T_Model")

class DataMapper(Generic[T_Entity, T_Model]):
    """Interface for mapping between Database Models and Domain Entities."""

    @staticmethod
    def to_domain(model: T_Model) -> T_Entity:
        """Convert Database Model to Domain Entity."""
        raise NotImplementedError

    @staticmethod
    def to_model(entity: T_Entity) -> T_Model:
        """Convert Domain Entity to Database Model."""
        raise NotImplementedError
