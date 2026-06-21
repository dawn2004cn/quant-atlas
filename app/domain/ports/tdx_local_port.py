"""Backward-compat re-exports for TDX ports.

Consolidated into ``tdx_ports.py``.  Kept for import compatibility.
"""

from __future__ import annotations

import warnings

from .tdx_ports import (
    PytdxMarketPort,
    TdxBaseDataWritePort,
    TdxBlockReadPort,
    TdxDaykSyncSessionPort,
    TdxDaykWritePort,
    TdxFinancePort,
    TdxGpcwRepository,
    TdxLocalFilePort,
)

warnings.warn(
    "Importing from tdx_local_port.py is deprecated. "
    "Use 'from app.domain.ports.tdx_ports import TdxLocalFilePort' instead.",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = [
    "TdxLocalFilePort",
    "TdxDaykWritePort",
    "TdxDaykSyncSessionPort",
    "TdxGpcwRepository",
    "TdxFinancePort",
    "TdxBlockReadPort",
    "PytdxMarketPort",
]
