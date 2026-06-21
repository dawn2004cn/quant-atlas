"""Deprecation policy for ``app.application.services`` compatibility shims."""

from __future__ import annotations

import warnings

_WARNED: set[str] = set()


def warn_shim_import(module: str) -> None:
    """Emit one DeprecationWarning per shim module per process."""
    if module in _WARNED:
        return
    _WARNED.add(module)
    warnings.warn(
        f"{module} is a compatibility shim; import from app.modules.* instead.",
        DeprecationWarning,
        stacklevel=3,
    )
