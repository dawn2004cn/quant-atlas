from __future__ import annotations

"""TimescaleDB repository for market bar time-series (raw / QFQ / HFQ + factors)."""

import threading
from datetime import datetime
from typing import Any

from app.core.logger import get_logger
from app.core.runtime_config import get_runtime_bool, get_runtime_int
from app.infrastructure.database.postgres_client import ensure_timescaledb_extension, postgres_connect
from app.infrastructure.database.postgres_settings import PostgresSettings
from app.infrastructure.repositories.common.factory import RepositoryType, register_repo
from app.infrastructure.repositories.postgres.timescale_adjusted_views import (
    ensure_adjusted_materialized_views,
    refresh_adjusted_materialized_views,
)
from app.infrastructure.tdx_local.qfq_calculator import apply_hfq_to_rows, apply_qfq_to_rows

logger = get_logger(__name__)

_SCHEMA_LOCK = threading.Lock()
_SCHEMA_READY = False

_BATCH_CHUNK = 1500

_OHLCV_DDL = """
    time TIMESTAMPTZ NOT NULL,
    symbol TEXT NOT NULL,
    market TEXT NOT NULL,
    open DOUBLE PRECISION,
    high DOUBLE PRECISION,
    low DOUBLE PRECISION,
    close DOUBLE PRECISION,
    volume DOUBLE PRECISION,
    amount DOUBLE PRECISION,
    source TEXT,
    PRIMARY KEY (time, symbol, market)
"""

_FACTOR_DDL = """
CREATE TABLE IF NOT EXISTS market_adjustment_factors (
    time TIMESTAMPTZ NOT NULL,
    symbol TEXT NOT NULL,
    market TEXT NOT NULL,
    factor DOUBLE PRECISION NOT NULL,
    source TEXT,
    PRIMARY KEY (time, symbol, market)
);
"""

_RAW_TABLE = "market_bars"
_LEGACY_ADJUSTED_TABLES = ("market_bars_qfq", "market_bars_hfq")

_BAR_UPSERT_SQL = f"""
    INSERT INTO {_RAW_TABLE}
        (time, symbol, market, open, high, low, close, volume, amount, source)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    ON CONFLICT (time, symbol, market) DO UPDATE SET
        open = EXCLUDED.open,
        high = EXCLUDED.high,
        low = EXCLUDED.low,
        close = EXCLUDED.close,
        volume = EXCLUDED.volume,
        amount = EXCLUDED.amount,
        source = EXCLUDED.source
"""

_FACTOR_UPSERT_SQL = """
    INSERT INTO market_adjustment_factors
        (time, symbol, market, factor, source)
    VALUES (%s, %s, %s, %s, %s)
    ON CONFLICT (time, symbol, market) DO UPDATE SET
        factor = EXCLUDED.factor,
        source = EXCLUDED.source
"""


def _create_bar_table_sql(table: str) -> str:
    return f"CREATE TABLE IF NOT EXISTS {table} ({_OHLCV_DDL});"


def _bar_ts(bar: dict[str, Any]) -> Any:
    return bar.get("time") or bar.get("date") or bar.get("timestamp")


def _use_adjusted_matviews() -> bool:
    return get_runtime_bool("TIMESCALE_USE_ADJUSTED_MATVIEWS", True)


def _store_adjusted_bars() -> bool:
    """旧模式：物理写入 qfq/hfq 表（默认关闭，改用物化视图）。"""
    if _use_adjusted_matviews():
        return False
    return get_runtime_bool("TIMESCALE_STORE_ADJUSTED_BARS", False)


def _relation_for_adjust(adjust: str) -> str:
    key = adjust if adjust in ("raw", "qfq", "hfq") else "raw"
    if key == "raw":
        return _RAW_TABLE
    if _use_adjusted_matviews():
        from app.infrastructure.repositories.postgres.timescale_adjusted_views import (
            MATVIEW_HFQ,
            MATVIEW_QFQ,
        )

        return MATVIEW_QFQ if key == "qfq" else MATVIEW_HFQ
    return "market_bars_qfq" if key == "qfq" else "market_bars_hfq"


def _batch_chunk_size() -> int:
    return max(100, min(get_runtime_int("TIMESCALE_UPSERT_BATCH_SIZE", _BATCH_CHUNK), 8000))


def _ensure_schema_once(postgres: PostgresSettings) -> None:
    global _SCHEMA_READY
    if _SCHEMA_READY:
        return
    with _SCHEMA_LOCK:
        if _SCHEMA_READY:
            return
        conn = postgres_connect(postgres, autocommit=False)
        try:
            ensure_timescaledb_extension(conn)
            with conn.cursor() as cur:
                cur.execute(_create_bar_table_sql(_RAW_TABLE))
                cur.execute(
                    f"SELECT create_hypertable('{_RAW_TABLE}', 'time', if_not_exists => TRUE)"
                )
                cur.execute(_FACTOR_DDL)
                cur.execute(
                    "SELECT create_hypertable('market_adjustment_factors', 'time', if_not_exists => TRUE)"
                )
                if _use_adjusted_matviews():
                    ensure_adjusted_materialized_views(cur)
                elif _store_adjusted_bars():
                    for table in _LEGACY_ADJUSTED_TABLES:
                        cur.execute(_create_bar_table_sql(table))
                        cur.execute(
                            f"SELECT create_hypertable('{table}', 'time', if_not_exists => TRUE)"
                        )
            conn.commit()
            _SCHEMA_READY = True
            logger.info(
                "TimescaleDB ready: %s + market_adjustment_factors (matviews=%s)",
                _RAW_TABLE,
                _use_adjusted_matviews(),
            )
        except Exception as exc:
            conn.rollback()
            logger.warning("TimescaleDB schema ensure skipped: %s", exc)
        finally:
            conn.close()


class TimescaleSyncSession:
    """One connection per worker thread; batch upsert + per-symbol commit."""

    def __init__(self, conn: Any, *, postgres: PostgresSettings) -> None:
        self._conn = conn
        self._postgres = postgres
        self._cur = conn.cursor()
        self._closed = False

    def write_ohlcv_package(
        self,
        *,
        symbol: str,
        market: str,
        raw_rows: list[dict[str, Any]],
        factors: list[dict[str, Any]],
        source: str = "tdx_dayk_sync",
    ) -> dict[str, int]:
        if not raw_rows:
            return {"raw": 0, "factors": 0, "qfq": 0, "hfq": 0}

        out: dict[str, int] = {
            "raw": _batch_write_bars(
                self._cur, table=_RAW_TABLE, symbol=symbol, market=market,
                bars=raw_rows, source=source,
            ),
            "factors": _batch_write_factors(
                self._cur, symbol=symbol, market=market, factors=factors, source=source,
            ),
            "qfq": 0,
            "hfq": 0,
        }
        if _store_adjusted_bars():
            qfq_rows = apply_qfq_to_rows(raw_rows, factors)
            hfq_rows = apply_hfq_to_rows(raw_rows, factors)
            out["qfq"] = _batch_write_bars(
                self._cur, table="market_bars_qfq", symbol=symbol, market=market,
                bars=qfq_rows, source=source,
            )
            out["hfq"] = _batch_write_bars(
                self._cur, table="market_bars_hfq", symbol=symbol, market=market,
                bars=hfq_rows, source=source,
            )
        return out

    def commit(self) -> None:
        if not self._closed:
            self._conn.commit()

    def rollback(self) -> None:
        if not self._closed:
            self._conn.rollback()

    def close(self) -> None:
        if self._closed:
            return
        try:
            self._cur.close()
        finally:
            self._conn.close()
            self._closed = True


def _batch_write_bars(
    cur: Any,
    *,
    table: str,
    symbol: str,
    market: str,
    bars: list[dict[str, Any]],
    source: str,
) -> int:
    if table != _RAW_TABLE and table in _LEGACY_ADJUSTED_TABLES:
        sql = f"""
            INSERT INTO {table}
                (time, symbol, market, open, high, low, close, volume, amount, source)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (time, symbol, market) DO UPDATE SET
                open = EXCLUDED.open, high = EXCLUDED.high, low = EXCLUDED.low,
                close = EXCLUDED.close, volume = EXCLUDED.volume,
                amount = EXCLUDED.amount, source = EXCLUDED.source
        """
    else:
        sql = _BAR_UPSERT_SQL
    batch: list[tuple[Any, ...]] = []
    for bar in bars:
        ts = _bar_ts(bar)
        if not ts:
            continue
        batch.append(
            (
                ts,
                symbol,
                market,
                bar.get("open"),
                bar.get("high"),
                bar.get("low"),
                bar.get("close"),
                bar.get("volume"),
                bar.get("amount"),
                source or bar.get("source"),
            )
        )
    chunk = _batch_chunk_size()
    for i in range(0, len(batch), chunk):
        part = batch[i : i + chunk]
        if part:
            cur.executemany(sql, part)
    return len(batch)


def _batch_write_factors(
    cur: Any,
    *,
    symbol: str,
    market: str,
    factors: list[dict[str, Any]],
    source: str,
) -> int:
    batch: list[tuple[Any, ...]] = []
    for fac in factors:
        ts = fac.get("date") or fac.get("time")
        if not ts:
            continue
        batch.append((ts, symbol, market, float(fac.get("factor", 1.0) or 1.0), source))
    chunk = _batch_chunk_size()
    for i in range(0, len(batch), chunk):
        part = batch[i : i + chunk]
        if part:
            cur.executemany(_FACTOR_UPSERT_SQL, part)
    return len(batch)


@register_repo(RepositoryType.POSTGRES, "market_bars")
class PostgresTimescaleBarRepository:
    """OHLCV + 复权因子；前/后复权默认由物化视图 ``market_bars_qfq`` / ``market_bars_hfq`` 派生。"""

    def __init__(self, postgres: PostgresSettings | None = None, *, autocommit: bool = False) -> None:
        if postgres is None:
            raise ValueError("PostgresSettings is required for PostgresTimescaleBarRepository")
        self._postgres = postgres
        self._autocommit = autocommit

    def ensure_schema(self) -> None:
        _ensure_schema_once(self._postgres)

    def open_sync_session(self) -> TimescaleSyncSession:
        _ensure_schema_once(self._postgres)
        conn = postgres_connect(self._postgres, autocommit=False)
        return TimescaleSyncSession(conn, postgres=self._postgres)

    def upsert_bars(
        self,
        *,
        symbol: str,
        market: str,
        bars: list[dict[str, Any]],
        source: str = "",
    ) -> int:
        """仅写入未复权 ``market_bars``（兼容旧调用）。"""
        if not bars:
            return 0
        session = self.open_sync_session()
        try:
            written = session.write_ohlcv_package(
                symbol=symbol,
                market=market,
                raw_rows=bars,
                factors=[],
                source=source,
            )["raw"]
            session.commit()
            return written
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def upsert_ohlcv_package(
        self,
        *,
        symbol: str,
        market: str,
        raw_rows: list[dict[str, Any]],
        factors: list[dict[str, Any]],
        source: str = "tdx_dayk_sync",
    ) -> dict[str, int]:
        """单次连接写入（兼容）；TDX 同步请用 ``open_sync_session``。"""
        if not raw_rows:
            return {"raw": 0, "factors": 0, "qfq": 0, "hfq": 0}
        session = self.open_sync_session()
        try:
            out = session.write_ohlcv_package(
                symbol=symbol,
                market=market,
                raw_rows=raw_rows,
                factors=factors,
                source=source,
            )
            session.commit()
            return out
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def get_bars(
        self,
        *,
        symbol: str,
        market: str,
        start: datetime | str | None = None,
        end: datetime | str | None = None,
        limit: int = 5000,
        adjust: str = "raw",
    ) -> list[dict[str, Any]]:
        """``adjust``: ``raw`` | ``qfq`` | ``hfq``（后两者读物化视图）。"""
        table = _relation_for_adjust(adjust)
        _ensure_schema_once(self._postgres)
        conn = postgres_connect(self._postgres, autocommit=True)
        try:
            clauses = ["symbol = %s", "market = %s"]
            params: list[Any] = [symbol, market]
            if start is not None:
                clauses.append("time >= %s")
                params.append(start)
            if end is not None:
                clauses.append("time <= %s")
                params.append(end)
            params.append(max(1, min(limit, 50000)))
            sql = (
                "SELECT time, symbol, market, open, high, low, close, volume, amount, source "
                f"FROM {table} WHERE {' AND '.join(clauses)} ORDER BY time ASC LIMIT %s"
            )
            with conn.cursor() as cur:
                cur.execute(sql, params)
                rows = cur.fetchall()
            return [
                {
                    "time": row[0],
                    "symbol": row[1],
                    "market": row[2],
                    "open": row[3],
                    "high": row[4],
                    "low": row[5],
                    "close": row[6],
                    "volume": row[7],
                    "amount": row[8],
                    "source": row[9],
                }
                for row in rows
            ]
        finally:
            conn.close()

    def get_factors(
        self,
        *,
        symbol: str,
        market: str,
        start: datetime | str | None = None,
        end: datetime | str | None = None,
        limit: int = 10000,
    ) -> list[dict[str, Any]]:
        _ensure_schema_once(self._postgres)
        conn = postgres_connect(self._postgres, autocommit=True)
        try:
            clauses = ["symbol = %s", "market = %s"]
            params: list[Any] = [symbol, market]
            if start is not None:
                clauses.append("time >= %s")
                params.append(start)
            if end is not None:
                clauses.append("time <= %s")
                params.append(end)
            params.append(max(1, min(limit, 50000)))
            sql = (
                "SELECT time, symbol, market, factor, source "
                f"FROM market_adjustment_factors WHERE {' AND '.join(clauses)} "
                "ORDER BY time ASC LIMIT %s"
            )
            with conn.cursor() as cur:
                cur.execute(sql, params)
                rows = cur.fetchall()
            return [
                {
                    "time": row[0],
                    "date": str(row[0])[:10],
                    "symbol": row[1],
                    "market": row[2],
                    "factor": row[3],
                    "source": row[4],
                }
                for row in rows
            ]
        finally:
            conn.close()

    def refresh_adjusted_materialized_views(self, *, concurrently: bool = True) -> None:
        """全量/批量写入 raw+因子后刷新前/后复权物化视图。"""
        if not _use_adjusted_matviews():
            return
        _ensure_schema_once(self._postgres)
        conn = postgres_connect(self._postgres, autocommit=False)
        try:
            refresh_adjusted_materialized_views(conn, concurrently=concurrently)
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()


class NullPostgresTimescaleBarRepository:
    """No-op when TimescaleDB is disabled."""

    def ensure_schema(self) -> None:
        return None

    def open_sync_session(self) -> Any:
        return None

    def upsert_bars(
        self,
        *,
        symbol: str,
        market: str,
        bars: list[dict[str, Any]],
        source: str = "",
    ) -> int:
        return 0

    def upsert_ohlcv_package(
        self,
        *,
        symbol: str,
        market: str,
        raw_rows: list[dict[str, Any]],
        factors: list[dict[str, Any]],
        source: str = "",
    ) -> dict[str, int]:
        return {"raw": 0, "factors": 0, "qfq": 0, "hfq": 0}

    def get_bars(
        self,
        *,
        symbol: str,
        market: str,
        start: datetime | str | None = None,
        end: datetime | str | None = None,
        limit: int = 5000,
        adjust: str = "raw",
    ) -> list[dict[str, Any]]:
        return []

    def get_factors(
        self,
        *,
        symbol: str,
        market: str,
        start: datetime | str | None = None,
        end: datetime | str | None = None,
        limit: int = 10000,
    ) -> list[dict[str, Any]]:
        return []

    def refresh_adjusted_materialized_views(self, *, concurrently: bool = True) -> None:
        return None
