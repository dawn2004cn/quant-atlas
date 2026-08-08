from __future__ import annotations
"""Cache TDX lday universe (avoid re-scanning all markets on every backfill batch)."""

from pathlib import Path
from typing import Any

from app.modules.data.services.tdx_ohlcv_reader import require_tdx_root
from app.core.logger import get_logger

logger = get_logger(__name__)

_CACHE: dict[str, Any] = {"root": "", "codes": []}


def get_tdx_cn_universe(*, force_refresh: bool = False) -> list[str]:
    """Return sorted canonical codes ``sh600519`` for current ``TDX_ROOT_PATH``."""
    root = require_tdx_root()
    key = str(root)
    if not force_refresh and _CACHE.get("root") == key and _CACHE.get("codes"):
        return list(_CACHE["codes"])

    from app.modules.data.services.tdx_dayk_sync_service import TdxDaykSyncService

    codes = TdxDaykSyncService.scan_cn_codes_from_tdx_dayk(Path(root))
    _CACHE["root"] = key
    _CACHE["codes"] = codes
    logger.info("tdx_code_cache: loaded %d codes from %s", len(codes), key)
    return list(codes)


def invalidate_tdx_code_cache() -> None:
    _CACHE["root"] = ""
    _CACHE["codes"] = []
