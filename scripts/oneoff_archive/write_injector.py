import pathlib
import textwrap

code = r"""
"""Annotation-driven service injector (DI 2.0).

Replaces the procedural ``wire_*`` helpers in ``wiring_*.py``.
Every function is replaced by a single ``inject()`` call that reads
constructor type annotations and resolves dependencies automatically.

Usage::

    from app.bootstrap_components.injector import ServiceInjector

    injector = ServiceInjector(services)
    injector.inject(AiAnalysisService)           # reads __init__ annotations
    injector.inject(AiCommitteeService,          # explicit overrides
                    stock_service=services.stock_service)
    injector.wire_all([AiAnalysisService, ...])  # batch
"""

from __future__ import annotations

import functools
import logging
import threading
from typing import Any, get_type_hints

logger = logging.getLogger(__name__)


class InjectionError(Exception):
    """Raised when a dependency cannot be resolved for a service."""


class ServiceInjector:
    """Annotation-driven service injector.

    ``services`` is a flat bundle object whose attributes are existing
    service instances (the ``Services`` class from ``create_services()``).
    """

    def __init__(self, services: Any) -> None:
        self._services = services
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def inject(
        self,
        service_cls: type,
        **explicit_overrides: Any,
    ) -> Any:
        """Construct *service_cls* by resolving its ``__init__`` annotations.

        Steps:
        1. Read type hints on ``__init__`` (excluding ``self`` and ``return``).
        2. For each parameter, look up an attribute on ``self._services`` with
           a matching name and compatible type.
        3. Pass resolved values to the constructor.

        Returns the constructed instance (also stored on ``services.<attr>``).
        """
        # Determine the target attribute name
        attr = _service_attr_name(service_cls)

        # Already injected?
        existing = getattr(self._services, attr, None)
        if existing is not None:
            return existing

        with self._lock:
            hints = _resolved_hints(service_cls)
            kwargs: dict[str, Any] = {}

            for param_name, param_type in hints.items():
                # 1. Explicit override wins
                if param_name in explicit_overrides:
                    kwargs[param_name] = explicit_overrides[param_name]
                    continue

                # 2. Try attribute with exact name first
                val = getattr(self._services, param_name, _MISSING)
                if val is not _MISSING:
                    kwargs[param_name] = val
                    continue

                # 3. Try alternative naming conventions
                alt_name = _infer_service_attr(param_name)
                if alt_name != param_name:
                    val = getattr(self._services, alt_name, _MISSING)
                    if val is not _MISSING:
                        kwargs[param_name] = val
                        continue

                # 4. Try empty constructor for missing params
                if _is_optional(param_type):
                    kwargs[param_name] = None
                    continue

                raise InjectionError(
                    f"Cannot resolve '{param_name}: {_type_name(param_type)}' "
                    f"for {service_cls.__name__}"
                )

            instance = service_cls(**kwargs)
            setattr(self._services, attr, instance)
            logger.debug("Injector created %s (args=%s)", attr, list(kwargs))
            return instance

    def wire_all(
        self,
        service_classes: list[type],
        *,
        in_order: bool = False,
        **shared_overrides: Any,
    ) -> list[Any]:
        """Batch-construct several services.

        By default each service is constructed independently (topological
        sort is NOT applied).  Pass ``in_order=True`` to build them in the
        provided sequence so earlier results are visible to later ones.
        """
        results: list[Any] = []
        for cls in service_classes:
            try:
                inst = self.inject(cls, **shared_overrides)
                results.append(inst)
            except InjectionError as exc:
                logger.warning("Injector skipped %s: %s", cls.__name__, exc)
                results.append(None)
        return results


# ------------------------------------------------------------------
# Internal helpers
# ------------------------------------------------------------------

_MISSING = object()


def _resolved_hints(cls: type) -> dict[str, type]:
    """Return dict of {param_name: type} from __init__, minus self/return."""
    import sys

    hints: dict[str, type] = {}
    # get_type_hints resolves forward references
    try:
        raw = get_type_hints(cls.__init__)
    except Exception:
        # fallback to __annotations__
        raw = getattr(cls.__init__, "__annotations__", {})

    for name, typ in raw.items():
        if name == "return":
            continue
        hints[name] = typ
    return hints


def _service_attr_name(cls: type) -> str:
    """Convert ``AiAnalysisService`` → ``ai_analysis_service``."""
    name = cls.__name__
    # CamelCase to snake_case
    result: list[str] = []
    for i, ch in enumerate(name):
        if ch.isupper() and i > 0:
            result.append("_")
        result.append(ch.lower())
    return "".join(result)


_SERVICE_SUFFIXES = frozenset({"service", "provider", "adapter", "facade", "gateway", "handler"})


def _infer_service_attr(name: str) -> str:
    """Map constructor param names back to ``services`` attribute names.

    Examples::

        stock_repository  → stock_repository    (exact)
        stock_svc         → stock_service       (suffix normalisation)
        market            → market_service      (common short form)
    """
    # Exact match already checked upstream
    for suffix in _SERVICE_SUFFIXES:
        if not name.endswith(suffix):
            candidate = f"{name}_{suffix}" if not name.endswith("_") else f"{name}{suffix}"
            # Only suggest if the param doesn't already end in the suffix
            if not any(name.endswith(s) for s in _SERVICE_SUFFIXES):
                return candidate
    return name


def _is_optional(typ: type) -> bool:
    """Check if a type annotation allows None."""
    import typing

    origin = getattr(typ, "__origin__", None)
    if origin in (typing.Union,):
        args = getattr(typ, "__args__", ())
        return type(None) in args  # noqa: E721
    return False


def _type_name(typ: type) -> str:
    return getattr(typ, "__name__", str(typ))
"""

p = pathlib.Path("app/bootstrap_components/injector.py")
p.write_text(code.lstrip(), encoding="utf-8")
print("Created injector.py")
