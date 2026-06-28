from __future__ import annotations

"""Read latest bar close from TDX lday and qlib_bin."""

from datetime import date, timedelta
from pathlib import Path
from typing import Any

from app.config import BASE_DIR, get_settings
from app.core.logger import get_logger
from app.domain.shared.symbol_normalizer import SymbolNormalizer
from app.infrastructure.providers.cn_tdx_provider import _symbol_to_market_code
from app.infrastructure.tdx_local.lday_reader import read_lday_file, read_lday_file_with_qfq
from app.infrastructure.tdx_local.paths import TdxLocalPaths, resolve_tdx_root

logger = get_logger(__name__)


def _code6(symbol: str) -> str:
    return SymbolNormalizer.normalize_code(symbol)


def latest_tdx_bar(
    symbol: str,
    *,
    tdx_root: str | None = None,
    use_qfq: bool = True,
) -> dict[str, Any] | None:
    """Return latest TDX lday bar ``{date, close, ...}`` or ``None``."""
    root = resolve_tdx_root(tdx_root or get_settings().tdx_root_path)
    if not root:
        return None
    code6 = _code6(symbol)
    paths = TdxLocalPaths(root)
    market_prefix, _ = _symbol_to_market_code(code6)
    file_path = paths.lday_file_by_market(market=market_prefix, code6=code6)
    if not file_path.is_file():
        return None
    try:
        rows = (
            read_lday_file_with_qfq(file_path, market=market_prefix, code=code6, tail=1)
            if use_qfq
            else read_lday_file(file_path, tail=1)
        )
    except Exception as exc:
        logger.warning("latest_tdx_bar failed sym=%s: %s", symbol, exc)
        return None
    return rows[-1] if rows else None


def latest_qlib_bar(
    symbol: str,
    *,
    base_dir: Path | None = None,
    lookback_days: int = 30,
) -> dict[str, Any] | None:
    """Return latest qlib_bin daily bar or ``None``."""
    end_d = date.today()
    start_d = end_d - timedelta(days=max(5, lookback_days))
    try:
        from app.infrastructure.qlib.history_bars_reader import load_cn_daily_ohlcv_from_qlib_bin

        rows = load_cn_daily_ohlcv_from_qlib_bin(
            _code6(symbol),
            start_d.isoformat(),
            end_d.isoformat(),
            base_dir=base_dir or BASE_DIR,
        )
    except Exception as exc:
        logger.warning("latest_qlib_bar failed sym=%s: %s", symbol, exc)
        return None
    return rows[-1] if rows else None


def latest_akshare_bar(symbol: str, *, lookback_days: int = 10) -> dict[str, Any] | None:
    """Return latest AkShare qfq daily bar or ``None`` when unavailable."""
    end_d = date.today()
    start_d = end_d - timedelta(days=max(3, lookback_days))
    try:
        from app.infrastructure.providers.cn_akshare_history import fetch_cn_daily_qfq

        bars, _note = fetch_cn_daily_qfq(
            _code6(symbol),
            start_d.isoformat(),
            end_d.isoformat(),
        )
    except Exception as exc:
        logger.debug("latest_akshare_bar failed sym=%s: %s", symbol, exc)
        return None
    return bars[-1] if bars else None
