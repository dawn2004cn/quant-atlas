"""Repository factory and registry for multi-database support.

This module implements the Factory Pattern to create Repository instances
based on the database type configuration. New database backends (e.g., PostgreSQL)
can be added by creating new implementation classes and registering them here.
"""

from enum import Enum
from typing import Any
from collections.abc import Callable



class RepositoryType(Enum):
    """Supported database types for repositories."""
    MYSQL = "mysql"
    SQLITE = "sqlite"
    POSTGRES = "postgres"


class RepositoryRegistry:
    """Central registry for repository implementations.

    This registry maps (RepositoryType, model_name) pairs to their
    concrete implementation classes. New implementations can be registered
    via the @register decorator or by calling register() directly.
    """

    _registry: dict[tuple[RepositoryType, str], type] = {}

    @classmethod
    def register(cls, repo_type: RepositoryType, model_name: str, repo_class: type) -> None:
        """Register a repository implementation.

        Args:
            repo_type: The database type (MYSQL, SQLITE, POSTGRES)
            model_name: The model/repo name (e.g., "investment_manager", "basic_market_data")
            repo_class: The concrete repository class
        """
        key = (repo_type.value, model_name)
        cls._registry[key] = repo_class

    @classmethod
    def get(cls, repo_type: RepositoryType, model_name: str) -> type | None:
        """Get a registered repository class.

        Args:
            repo_type: The database type
            model_name: The model name

        Returns:
            The registered repository class, or None if not found
        """
        key = (repo_type.value, model_name)
        return cls._registry.get(key)

    @classmethod
    def list_registered(cls) -> list[tuple[str, str]]:
        """List all registered (type, model) pairs."""
        return [(k[0], k[1]) for k in cls._registry.keys()]


def register_repo(repo_type: RepositoryType, model_name: str) -> Callable:
    """Decorator to register a repository class.

    Usage:
        @register_repo(RepositoryType.MYSQL, "investment_manager")
        class MySQLInvestmentManagerRepository:
            ...
    """
    def decorator(cls: type) -> type:
        RepositoryRegistry.register(repo_type, model_name, cls)
        return cls
    return decorator


def create_repository(
    repo_type: RepositoryType,
    model_name: str,
    **kwargs: Any,
) -> Any:
    """Factory function to create a repository instance.

    Args:
        repo_type: The database type to use
        model_name: The model name (e.g., "investment_manager")
        **kwargs: Additional arguments passed to the repository constructor

    Returns:
        A repository instance of the appropriate type

    Raises:
        ValueError: If no repository is registered for the given type/model pair
    """
    repo_class = RepositoryRegistry.get(repo_type, model_name)
    if repo_class is None:
        available = RepositoryRegistry.list_registered()
        raise ValueError(
            f"No repository registered for ({repo_type.value}, {model_name}). "
            f"Available: {available}"
        )
    return repo_class(**kwargs)
