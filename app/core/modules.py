from __future__ import annotations

"""Legacy module manifest shim.

.. deprecated::
    Use ``app.core.registry.context_module_manifest`` instead.
    This module remains for backward-compatible imports only.
"""

from typing import Any


def module_manifest(*, config: dict[str, Any] | None = None) -> dict[str, Any]:
    """Deprecated alias of ``context_module_manifest``."""
    from app.core.registry import context_module_manifest

    return context_module_manifest(config=config)


__all__ = ["module_manifest"]
