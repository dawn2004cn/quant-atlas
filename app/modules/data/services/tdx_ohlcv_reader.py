from __future__ import annotations
"""Read CN daily OHLCV from TDX vipdoc lday files (single source of truth)."""

from datetime import date
from pathlib import Path
from typing import Any

from app.modules.system.services.helpers.tdx_local_access import get_tdx_local_file_port
from app.config import get_settings
from app.core.logger import get_logger
from app.domain.shared.symbol_normalizer import SymbolNormalizer
from app.domain.shared.tdx_paths import TdxLocalPaths, resolve_tdx_root

logger = get_logger(__name__)

_port_ready = False


def ensure_tdx_local_file_port() -> None:
    """CLI/Celery 路径未走 Flask bootstrap 时惰性绑定 TDX 文件端口。"""
    global _port_ready
    if _port_ready:
        return
    from app.modules.system.services.helpers.tdx_local_access import (
        bind_tdx_local_file_port,
        get_tdx_local_file_port,
    )

    try:
        get_tdx_local_file_port()
        _port_ready = True
        return
    except RuntimeError:
        logger.warning("Suppressed exception", exc_info=True)
        pass
    from app.bootstrap_components.providers import create_tdx_local_file_port

    bind_tdx_local_file_port(create_tdx_local_file_port())
    _port_ready = True


def require_tdx_root() -> Path:
    root = resolve_tdx_root(get_settings().tdx_root_path)
    if root is None:
        raise ValueError("TDX_ROOT_PATH not configured")
    return Path(root).resolve()


def scan_tdx_cn_codes(
    *,
    limit: int | None = None,
    offset: int = 0,
    tdx_root: Path | None = None,
) -> list[str]:
    """Scan ``sh/sz/bj`` lday directory for canonical codes ``sh600519``."""
    if tdx_root is not None:
        from app.modules.data.services.tdx_dayk_sync_service import TdxDaykSyncService

        codes = TdxDaykSyncService.scan_cn_codes_from_tdx_dayk(Path(tdx_root))
    else:
        from app.modules.data.services.tdx_code_cache import get_tdx_cn_universe

        codes = get_tdx_cn_universe()
    if offset or limit is not None:
        end = offset + limit if limit is not None else None
        return codes[offset:end]
    return codes


def _normalize_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_date: dict[str, dict[str, Any]] = {}
    for r in rows:
        d = str(r.get("date") or "")[:10]
        if not d:
            continue
        by_date[d] = {
            "date": d,
            "open": float(r.get("open") or 0),
            "high": float(r.get("high") or 0),
            "low": float(r.get("low") or 0),
            "close": float(r.get("close") or 0),
            "volume": float(r.get("volume") or 0),
            "amount": float(r.get("amount") or 0),
        }
    return [by_date[k] for k in sorted(by_date)]


def fetch_tdx_daily_bars(
    cn_symbol: str,
    start_d: date | None = None,
    end_d: date | None = None,
    *,
    tdx_root: Path | None = None,
) -> list[dict[str, Any]]:
    """Read full (or date-filtered) daily bars from TDX ``.day`` file."""
    root = tdx_root or require_tdx_root()
    paths = TdxLocalPaths(root)
    norm = SymbolNormalizer.normalize_cn_symbol(cn_symbol)
    if len(norm) < 8:
        return []
    market = norm[:2]
    code6 = norm[-6:]
    lday = paths.lday_file_by_market(market=market, code6=code6)
    if not lday.is_file():
        return []
    try:
        ensure_tdx_local_file_port()
        rows = _normalize_rows(get_tdx_local_file_port().read_lday_file(lday, tail=None))
    except Exception as exc:  # noqa: BLE001
        logger.debug("fetch_tdx_daily_bars %s: %s", norm, exc)
        return []
    if start_d is None and end_d is None:
        return rows
    start_s = start_d.isoformat() if start_d else ""
    end_s = end_d.isoformat() if end_d else "2099-12-31"
    return [r for r in rows if start_s <= r["date"] <= end_s]
