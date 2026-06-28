from __future__ import annotations

"""Module auto-discovery scanner.

Uses ``app.core.registry`` for route discovery (replaces legacy ``core.modules``).
"""

import importlib
import logging
import pkgutil
from typing import Any

from flask import Blueprint

logger = logging.getLogger(__name__)


def scan_and_register_modules(
    blueprint: Blueprint,
    ctx: Any,
    *,
    scan_package: str = "app.modules",
    config: dict[str, Any] | None = None,
) -> int:
    """Scan context modules and register their routes via the declarative registry.

    Returns the number of routes registered.
    """
    try:
        pkg = importlib.import_module(scan_package)
    except ImportError:
        logger.warning("Module scan package %r not found", scan_package)
        return 0

    discovered = 0
    for _finder, name, _ispkg in pkgutil.iter_modules(pkg.__path__, prefix=f"{scan_package}."):
        try:
            importlib.import_module(name)
            discovered += 1
        except Exception as exc:
            logger.warning("Module scan skipped %s: %s", name, exc)

    if discovered:
        logger.info("Module scanner discovered %d packages under %s", discovered, scan_package)

    from app.core.registry import discover_modules, discover_routes
    from app.presentation.api.route_loader import preload_route_modules

    preload_route_modules()
    enabled = {m.name for m in discover_modules(config=config)}
    if enabled:
        logger.debug("Enabled context modules: %s", ", ".join(sorted(enabled)))

    registered = 0
    for name, register_fn in discover_routes(config=config):
        try:
            register_fn(blueprint, ctx)
            registered += 1
        except Exception as exc:
            logger.warning("Module route registration failed for %s: %s", name, exc)
    return registered


__all__ = ["scan_and_register_modules"]
