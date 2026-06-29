"""Legacy re-exports. Use ``app.infrastructure.memory_cache`` for new code."""

# Lazy import via __getattr__ — avoids application → infra at load time
from typing import Any


def __getattr__(name: str) -> Any:
    import importlib
    mod = importlib.import_module("app.infrastructure.memory_cache")
    return getattr(mod, name)


def get_hot_path_cache():
    return __import__("app.infrastructure.memory_cache", fromlist=["get_cache"]).get_cache

POLICIES = {}

__all__ = ["CacheTier", "CachePolicy", "POLICIES", "HotPathCache", "get_hot_path_cache"]