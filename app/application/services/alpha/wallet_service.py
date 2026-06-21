"""Backward-compat re-export for ``WalletService`` and ``WalletEntry``."""
from __future__ import annotations

from app.modules.system.services.alpha.wallet_service import (
    WalletEntry,
    WalletService,
)

__all__ = [
    "WalletEntry",
    "WalletService",
]
