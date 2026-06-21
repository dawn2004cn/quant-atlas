"""Domain module exports."""

from __future__ import annotations

import importlib
from .entities import *

_DOMAIN_SUBMODULES = {
    "alpha",
    "risk",
    "execution",
    "regime",
    "optimization",
    "compute",
    "ports",
    "services",
}

__all__ = list(_DOMAIN_SUBMODULES)


def __getattr__(name: str):
    if name in _DOMAIN_SUBMODULES:
        module = importlib.import_module(f"app.domain.{name}")
        globals()[name] = module
        return module
    raise AttributeError(f"module 'app.domain' has no attribute {name!r}")
