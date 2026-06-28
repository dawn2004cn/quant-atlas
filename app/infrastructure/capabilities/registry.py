from __future__ import annotations

"""Capability registry – service locator & self-registration decorator."""


from typing import Any

from app.domain.capabilities.base import BaseCapability

# ── global class registry (decorator-populated) ──────────────────────────
_registry: dict[str, type[BaseCapability]] = {}


def capability(name: str):
    """Decorator that self-registers a ``BaseCapability`` subclass.

    Usage::

        @capability("fetch_bars")
        class BarsCapability(BaseCapability):
            capability_name = "fetch_bars"
            ...
    """
    def _inner(cls: type[BaseCapability]) -> type[BaseCapability]:
        _registry[name] = cls
        return cls
    return _inner


def _list_registered() -> list[str]:
    return list(_registry.keys())


# ── runtime registry ─────────────────────────────────────────────────────


class CapabilityRegistry:
    """Runtime registry that instantiates capabilities on demand.

    Each capability class receives the same dependency dict so it can pull
    whatever services it needs from its constructor.
    """

    def __init__(self, **dependencies: Any) -> None:
        self._dependencies = dependencies
        self._instances: dict[str, BaseCapability] = {}

    def get(self, name: str) -> BaseCapability:
        """Return (and lazily create) the named capability instance."""
        cls = _registry.get(name)
        if cls is None:
            raise KeyError(f"Unknown capability: {name!r}. Available: {list(_registry)}")
        if name not in self._instances:
            self._instances[name] = cls(**self._dependencies)
        return self._instances[name]

    def execute(self, name: str, **kwargs: Any) -> tuple[Any, str]:
        """Look up the capability and call ``execute(**kwargs)``."""
        cap = self.get(name)
        return cap.execute(**kwargs)

    def list_capabilities(self) -> list[str]:
        return _list_registered()

    @property
    def available(self) -> list[str]:
        return self.list_capabilities()
