from __future__ import annotations

"""Build QuestDB / ClickHouse adapters from environment settings."""

from typing import Any

from app.domain.ports.timeseries_port import TimeSeriesDBPort
from app.infrastructure.database.timeseries_settings import (
    ClickHouseSettings,
    QuestDBSettings,
    load_clickhouse_settings,
    load_questdb_settings,
)
from app.infrastructure.timeseries.adapters import (
    ClickHouseAdapter,
    QuestDBAdapter,
)


def create_questdb_adapter(settings: QuestDBSettings | None = None) -> QuestDBAdapter | None:
    cfg = settings or load_questdb_settings()
    if cfg is None:
        return None
    from app.core.runtime_config import get_runtime_bool

    return QuestDBAdapter(
        host=cfg.host,
        http_port=cfg.http_port,
        pg_port=cfg.pg_port,
        user=cfg.user,
        password=cfg.password,
        database=cfg.database,
        use_pg_wire=get_runtime_bool("QUESTDB_USE_PG_WIRE", True),
    )


def create_clickhouse_adapter(settings: ClickHouseSettings | None = None) -> ClickHouseAdapter | None:
    cfg = settings or load_clickhouse_settings()
    if cfg is None:
        return None
    return ClickHouseAdapter(
        host=cfg.host,
        port=cfg.port,
        user=cfg.user,
        password=cfg.password,
        database=cfg.database,
    )


def timeseries_health_probe() -> dict[str, Any]:
    """Ping QuestDB HTTP and ClickHouse HTTP; safe for API exposure (no secrets)."""
    from app.infrastructure.timeseries.ohlcv_history_reader import probe_ohlcv_tables

    out: dict[str, Any] = {"ok": True, "questdb": None, "clickhouse": None}
    q_cfg = load_questdb_settings()
    if q_cfg is not None:
        adapter = create_questdb_adapter(q_cfg)
        connected = adapter.connect() if adapter else False
        out["questdb"] = {
            "enabled": True,
            "connected": connected,
            "endpoint": q_cfg.describe(),
            "http_port": q_cfg.http_port,
            "pg_port": q_cfg.pg_port,
            "ilp_port": q_cfg.ilp_port,
        }
        if adapter:
            adapter.disconnect()
    else:
        out["questdb"] = {"enabled": False, "reason": "QUESTDB_HOST unset or ENABLE_QUESTDB=0"}

    ch_cfg = load_clickhouse_settings()
    if ch_cfg is not None:
        adapter = create_clickhouse_adapter(ch_cfg)
        connected = adapter.connect() if adapter else False
        out["clickhouse"] = {
            "enabled": True,
            "connected": connected,
            "endpoint": ch_cfg.describe(),
        }
        if adapter:
            adapter.disconnect()
    else:
        out["clickhouse"] = {"enabled": False, "reason": "CLICKHOUSE_HOST unset or ENABLE_CLICKHOUSE=0"}

    out["ok"] = True
    if (out["questdb"] or {}).get("enabled") and not (out["questdb"] or {}).get("connected"):
        out["ok"] = False
    if (out["clickhouse"] or {}).get("enabled") and not (out["clickhouse"] or {}).get("connected"):
        out["ok"] = False
    ohlcv = probe_ohlcv_tables()
    out["ohlcv_tables"] = ohlcv
    warnings: list[str] = []
    if (out["questdb"] or {}).get("enabled") and int(ohlcv.get("questdb_rows") or 0) < 1_000_000:
        warnings.append("questdb_backfill_recommended")
    q_sample = int(ohlcv.get("questdb_sample_sh600519") or 0)
    if (out["questdb"] or {}).get("enabled") and q_sample < 100:
        warnings.append("questdb_sample_sparse")
    if warnings:
        out["warnings"] = warnings
    from app.infrastructure.timeseries.sync_snapshot import (
        describe_questdb_sync_beat,
        describe_timeseries_backfill_status,
        get_timeseries_sync_progress,
        get_timeseries_sync_snapshot,
    )

    out["last_sync"] = get_timeseries_sync_snapshot()
    out["sync_progress"] = get_timeseries_sync_progress()
    out["celery_beat"] = describe_questdb_sync_beat()
    out["backfill"] = describe_timeseries_backfill_status()
    try:
        from app.config import get_settings
        from app.core.runtime_config import get_runtime
        from app.infrastructure.execution.qmt_executor import qmt_executor_status

        qmt = get_settings().qmt
        out["execution"] = {
            "default_mode": get_runtime("EXECUTION_DEFAULT_MODE", "paper"),
            "qmt": qmt_executor_status(
                account_id=qmt.account_id or "",
                qmt_path=qmt.qmt_path or "",
            ),
        }
    except Exception:
        out["execution"] = {"qmt": {"execution_mode": "disabled"}}
    return out


def get_timeseries_ports() -> dict[str, TimeSeriesDBPort]:
    """Named adapters for application wiring."""
    ports: dict[str, TimeSeriesDBPort] = {}
    q = create_questdb_adapter()
    if q is not None:
        ports["questdb"] = q
    ch = create_clickhouse_adapter()
    if ch is not None:
        ports["clickhouse"] = ch
    return ports
