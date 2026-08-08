from __future__ import annotations

"""TimescaleDB 双写：session、package upsert、物化视图刷新。"""

from typing import Any

from app.config import AppSettings
from app.core.logger import get_logger
from app.core.runtime_config import get_runtime_bool
from app.modules.data.services.tdx_dayk_sync_models import SyncResult
from app.modules.data.services.timescale_sync_session import (
    get_thread_timescale_session,
    set_thread_timescale_session,
)

logger = get_logger(__name__)

EMPTY_COUNTS = {"raw": 0, "factors": 0, "qfq": 0, "hfq": 0}


def open_timescale_sync_session() -> Any | None:
    from app.modules.system.services.helpers.timescale_bar_access import (
        ensure_timescale_bar_port,
        get_timescale_bar_port,
    )

    ensure_timescale_bar_port()
    port = get_timescale_bar_port()
    if port is None or not hasattr(port, "open_sync_session"):
        return None
    session = get_thread_timescale_session()
    if session is not None:
        return session
    session = port.open_sync_session()
    if session is None:
        return None
    set_thread_timescale_session(session)
    return session


def persist_timescale_package(
    settings: AppSettings,
    stock_code: str,
    raw_rows: list[dict[str, Any]],
    factors: list[dict[str, Any]],
    *,
    ts_session: Any | None = None,
) -> dict[str, int]:
    """USE_TIMESCALEDB=1 时写入 raw + 因子 + 前复权 + 后复权表。"""
    if not settings.use_timescaledb:
        return dict(EMPTY_COUNTS)

    from app.modules.system.services.helpers.timescale_bar_access import (
        ensure_timescale_bar_port,
        get_timescale_bar_port,
    )

    port = get_timescale_bar_port()
    if port is None:
        ensure_timescale_bar_port()
        port = get_timescale_bar_port()
    if port is None:
        raise RuntimeError(
            "TimescaleBarPort 未绑定；请设置 USE_TIMESCALEDB=1 并配置 TIMESCALEDB_*"
        )
    try:
        if ts_session is not None:
            return ts_session.write_ohlcv_package(
                symbol=stock_code,
                market="CN",
                raw_rows=raw_rows,
                factors=factors,
                source="tdx_dayk_sync",
            )
        return port.upsert_ohlcv_package(
            symbol=stock_code,
            market="CN",
            raw_rows=raw_rows,
            factors=factors,
            source="tdx_dayk_sync",
        )
    except Exception as exc:
        if get_runtime_bool("TDX_SYNC_STRICT_TARGETS", True):
            raise
        logger.warning("Timescale upsert failed for %s: %s", stock_code, exc)
        return dict(EMPTY_COUNTS)


def refresh_timescale_matviews(settings: AppSettings) -> None:
    if not settings.use_timescaledb:
        return
    if not get_runtime_bool("TIMESCALE_REFRESH_MATVIEWS_ON_SYNC", True):
        return
    from app.modules.system.services.helpers.timescale_bar_access import get_timescale_bar_port

    port = get_timescale_bar_port()
    if port is None or not hasattr(port, "refresh_adjusted_materialized_views"):
        return
    try:
        port.refresh_adjusted_materialized_views()
    except Exception as exc:
        logger.warning("Timescale matview refresh failed: %s", exc)


def apply_timescale_counts(result: SyncResult, counts: dict[str, int]) -> None:
    result.timescale_rows = int(counts.get("raw", 0))
    result.timescale_factor_rows = int(counts.get("factors", 0))
    result.timescale_qfq_rows = int(counts.get("qfq", 0))
    result.timescale_hfq_rows = int(counts.get("hfq", 0))
