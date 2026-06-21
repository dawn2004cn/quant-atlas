"""Route module preloader — populates @register_routes registry before discovery."""

from __future__ import annotations

import importlib
import logging
import pkgutil
from pathlib import Path

logger = logging.getLogger(__name__)

_ROUTE_MODULE_PREFIXES = ("routes_v1_", "routes_market_sentiment", "routes_metrics", "routes_v2", "routes_i18n")


def preload_route_modules(*, package: str = "app.presentation.api") -> int:
    """Import API route modules so ``@register_routes`` decorators run.

    Returns the number of modules successfully imported.
    """
    try:
        pkg = importlib.import_module(package)
    except ImportError as exc:
        logger.warning("Route preload package %r not found: %s", package, exc)
        return 0

    loaded = 0
    for _finder, name, _ispkg in pkgutil.iter_modules(pkg.__path__, prefix=f"{package}."):
        module_suffix = name.rsplit(".", 1)[-1]
        if not any(module_suffix.startswith(prefix) for prefix in _ROUTE_MODULE_PREFIXES):
            continue
        try:
            importlib.import_module(name)
            loaded += 1
        except Exception as exc:
            logger.warning("Route preload skipped %s: %s", name, exc)
    # v1 subpackages (stock routes split into routes_*.py modules)
    api_dir = Path(pkg.__file__).resolve().parent
    v1_dir = api_dir / "v1"
    if v1_dir.is_dir():
        for routes_file in sorted(v1_dir.rglob("routes_*.py")):
            rel = routes_file.relative_to(api_dir).with_suffix("")
            module_name = f"{package}.{rel.as_posix().replace('/', '.')}"
            try:
                importlib.import_module(module_name)
                loaded += 1
            except Exception as exc:
                logger.warning("Route preload skipped %s: %s", module_name, exc)

    if loaded:
        logger.debug("Preloaded %d route modules from %s", loaded, package)
    return loaded


__all__ = ["preload_route_modules"]
