"""Context-module driven service wiring (Phase 2 / Phase 4)."""

from __future__ import annotations

import importlib
import logging
import pkgutil
from typing import Any

logger = logging.getLogger(__name__)


from app.core.registry import get_module, list_modules


def discover_modules() -> list[Any]:
    """Discover all registered ContextModule classes."""
    return list_modules()


def _ensure_module_packages_loaded() -> None:
    """Ensure all module packages are loaded (legacy compatibility)."""
    for module in discover_modules():
        try:
            __import__(module.__module__)
        except Exception as exc:
            logger.debug("Module package load skipped: %s", exc)


def wire_context_modules(
    services: Any,
    session_factory: Any = None,
    *,
    config: dict[str, Any] | None = None,
) -> list[str]:
    """Wire services for all enabled context modules that declare ``wire``."""
    from app.core.registry import discover_modules

    _ensure_module_packages_loaded()
    wired: list[str] = []
    for module in discover_modules(config=config):
        wire_fn = module.wire
        if wire_fn is None:
            continue
        try:
            wire_fn(services, session_factory)
            wired.append(module.name)
            logger.debug("Wired context module: %s", module.name)
        except Exception as exc:
            logger.warning("Could not wire context module %s: %s", module.name, exc)
    if wired:
        logger.info("Context modules wired: %s", ", ".join(wired))
    return wired


def initialize_all_modules(
    container: Any,
    *,
    session_factory: Any = None,
    config: dict[str, Any] | None = None,
) -> list[str]:
    """Discover enabled ``@register_module`` contexts and invoke ``wire`` / ``initialize``."""
    try:
        import app.presentation.api.context_modules  # noqa: F401
    except Exception as exc:  # noqa: BLE001
        logger.warning("Context module preload skipped: %s", exc)

    _ensure_module_packages_loaded()
    from app.core.registry import discover_modules

    wired: list[str] = []
    for module in discover_modules(config=config or {}):
        init_fn = getattr(module, "initialize", None)
        if callable(init_fn):
            try:
                init_fn(container, session_factory)
                wired.append(module.name)
                continue
            except TypeError:
                try:
                    init_fn(container)
                    wired.append(module.name)
                    continue
                except Exception as exc:
                    logger.warning("Module initialize failed %s: %s", module.name, exc)
        wire_fn = module.wire
        if wire_fn is None:
            continue
        try:
            wire_fn(container, session_factory)
            wired.append(module.name)
        except Exception as exc:
            logger.warning("Could not wire context module %s: %s", module.name, exc)
    if wired:
        logger.info("Context modules initialized: %s", ", ".join(wired))
    return wired


__all__ = ["wire_context_modules", "initialize_all_modules"]
