"""Shared helpers for ``register_factory`` lazy service construction."""

from __future__ import annotations

import importlib
from collections.abc import Callable
from typing import Any


def zero_arg_service(module: str, class_name: str) -> Callable[[Any], Any]:
    """Return a registry factory that lazy-imports ``class_name`` from ``module``."""

    def _factory(_: Any) -> Any:
        cls = getattr(importlib.import_module(module), class_name)
        return cls()

    return _factory
