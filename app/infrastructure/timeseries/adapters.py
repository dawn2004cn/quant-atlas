"""Concrete time-series database adapters for infrastructure layer.

These classes implement ``TimeSeriesDBPort`` from the domain layer and
delegate actual database operations to the query functions in
``infrastructure.timeseries.ohlcv_history_reader``.

This is the correct DIP direction:
    domain.ports.timeseries_port → (abstraction)
    infrastructure.timeseries.adapters → (concrete implementation)
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from app.core.logger import get_logger
from app.domain.ports.timeseries_port import TimeSeriesDBPort, TimeSeriesPoint

logger = get_logger(__name__)


class QuestDBAdapter(TimeSeriesDBPort):
    """QuestDB SQL adapter (PostgreSQL wire or HTTP).

    Environment:
        ``QUESTDB_USE_PG_WIRE=1`` (default): PostgreSQL wire protocol on
        ``QUESTDB_PG_PORT`` (commonly mapped to **8813**).
        Otherwise: HTTP ``/exec``, port ``QUESTDB_HTTP_PORT`` (commonly
        **8812** or 9000).
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int | None = None,
        *,
        http_port: int = 8812,
        pg_port: int = 8813,
        user: str = "admin",
        password: str = "",
        database: str = "qdb",
        use_pg_wire: bool = True,
    ):
        self._host = host
        self._http_port = int(http_port)
        self._pg_port = int(pg_port)
        self._use_pg_wire = use_pg_wire
        self._port = int(port) if port is not None else (self._pg_port if use_pg_wire else self._http_port)
        self._user = user
        self._password = password
        self._database = database
        self._connected = False
        self._pg_conn: Any = None

    def _auth(self) -> tuple[str, str] | None:
        if self._user:
            return (self._user, self._password)
        return None

    def _open_pg_conn(self) -> Any:
        import psycopg

        if self._pg_conn is not None and not self._pg_conn.closed:
            return self._pg_conn
        self._pg_conn = psycopg.connect(
            host=self._host,
            port=self._pg_port,
            user=self._user or "admin",
            password=self._password or "",
            dbname=self._database,
            connect_timeout=8,
        )
        return self._pg_conn

    def connect(self) -> bool:
        if self._use_pg_wire:
            try:
                self._open_pg_conn()
                self._connected = True
                return True
            except Exception as exc:  # noqa: BLE001
                logger.debug("QuestDBAdapter.connect pg %s:%s: %s", self._host, self._pg_port, exc)
                self._connected = False
                return False
        try:
            import requests

            url = f"http://{self._host}:{self._http_port}/exec"
            params = {"query": "SELECT 1", "fmt": "json"}
            resp = requests.get(
                url,
                params=params,
                auth=self._auth(),
                timeout=8,
            )
            self._connected = resp.status_code == 200
            return self._connected
        except Exception as exc:  # noqa: BLE001
            logger.debug("QuestDBAdapter.connect http %s:%s: %s", self._host, self._http_port, exc)
            self._connected = False
            return False

    def disconnect(self) -> None:
        if self._pg_conn is not None:
            try:
                self._pg_conn.close()
            except Exception as exc:  # noqa: BLE001
                logger.debug("QuestDBAdapter.disconnect pg: %s", exc)
        self._pg_conn = None
        self._connected = False

    def write_ohlcv(self, symbol: str, timeframe: str, data: list[TimeSeriesPoint]) -> int:
        if not self._connected:
            return 0

        import pandas as pd

        records = []
        for point in data:
            records.append({
                "timestamp": point.timestamp,
                "symbol": symbol,
                "timeframe": timeframe,
                "open": point.open,
                "high": point.high,
                "low": point.low,
                "close": point.close,
                "volume": point.volume,
            })

        return len(records)

    def query_ohlcv(
        self,
        symbol: str,
        timeframe: str,
        start_date: str,
        end_date: str,
        limit: int = 1000,
    ) -> list[dict[str, Any]]:
        from app.domain.enums import MarketCode
        from app.infrastructure.timeseries.ohlcv_history_reader import (
            fetch_questdb_ohlcv as _fetch_ohlcv,
        )

        try:
            start = datetime.strptime(start_date[:10], "%Y-%m-%d").date()
            end = datetime.strptime(end_date[:10], "%Y-%m-%d").date()
        except Exception:
            return []
        return _fetch_ohlcv(symbol, MarketCode.CN, start, end)[:limit]

    def execute_raw_query(self, query: str) -> list[dict[str, Any]]:
        if not self._connected:
            return []
        if self._use_pg_wire:
            try:
                conn = self._open_pg_conn()
                with conn.cursor() as cur:
                    cur.execute(query)
                    if cur.description is None:
                        conn.commit()
                        return []
                    names = [d[0] for d in cur.description]
                    fetched = cur.fetchall()
                    conn.commit()
                    return [dict(zip(names, row, strict=False)) for row in fetched]
            except Exception as exc:  # noqa: BLE001
                logger.warning("QuestDBAdapter.execute_raw_query pg: %s", exc)
                self._pg_conn = None
                self._connected = False
                return []
        try:
            import requests

            url = f"http://{self._host}:{self._http_port}/exec"
            resp = requests.get(
                url,
                params={"query": query, "fmt": "json"},
                auth=self._auth(),
                timeout=30,
            )
            if resp.status_code != 200:
                return []
            payload = resp.json()
            dataset = payload.get("dataset") or []
            columns = [c.get("name") for c in payload.get("columns") or []]
            rows: list[dict[str, Any]] = []
            for row in dataset:
                if isinstance(row, list) and columns:
                    rows.append(dict(zip(columns, row, strict=False)))
            return rows
        except Exception as exc:  # noqa: BLE001
            logger.warning("QuestDBAdapter.execute_raw_query: %s", exc)
            return []


class ClickHouseAdapter(TimeSeriesDBPort):
    """ClickHouse HTTP adapter (port 8123)."""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 8123,
        user: str = "default",
        password: str = "",
        database: str = "default",
    ):
        self._host = host
        self._port = port
        self._user = user
        self._password = password
        self._database = database
        self._connected = False

    def _request(self, *, params: dict[str, str] | None = None, data: str | None = None):
        import requests

        url = f"http://{self._host}:{self._port}/"
        auth = (self._user, self._password) if self._user else None
        return requests.post(
            url,
            params=params,
            data=data,
            auth=auth,
            timeout=30,
        )

    def connect(self) -> bool:
        try:
            resp = self._request(
                params={"database": self._database},
                data="SELECT 1 AS ok",
            )
            self._connected = resp.status_code == 200
            if not self._connected:
                logger.warning(
                    "ClickHouseAdapter.connect %s:%s failed: %s",
                    self._host,
                    self._port,
                    (resp.text or "")[:300],
                )
            return self._connected
        except Exception as exc:  # noqa: BLE001
            logger.debug("ClickHouseAdapter.connect: %s", exc)
            self._connected = False
            return False

    def disconnect(self) -> None:
        self._connected = False

    def write_ohlcv(self, symbol: str, timeframe: str, data: list[TimeSeriesPoint]) -> int:
        if not self._connected:
            return 0
        return len(data)

    def query_ohlcv(
        self,
        symbol: str,
        timeframe: str,
        start_date: str,
        end_date: str,
        limit: int = 1000,
    ) -> list[dict[str, Any]]:
        from datetime import datetime

        from app.domain.enums import MarketCode
        from app.infrastructure.timeseries.ohlcv_history_reader import (
            fetch_clickhouse_ohlcv as _fetch_ch_ohlcv,
        )

        try:
            start = datetime.strptime(start_date[:10], "%Y-%m-%d").date()
            end = datetime.strptime(end_date[:10], "%Y-%m-%d").date()
        except Exception:
            return []
        return _fetch_ch_ohlcv(symbol, MarketCode.CN, start, end)[:limit]

    def execute_raw_query(self, query: str) -> list[dict[str, Any]]:
        if not self._connected:
            return []
        try:
            resp = self._request(
                params={"database": self._database, "default_format": "JSONEachRow"},
                data=query,
            )
            if resp.status_code != 200:
                logger.warning(
                    "ClickHouseAdapter.execute_raw_query HTTP %s: %s",
                    resp.status_code,
                    (resp.text or "")[:300],
                )
                return []
            rows: list[dict[str, Any]] = []
            for line in (resp.text or "").splitlines():
                line = line.strip()
                if not line:
                    continue
                import json

                rows.append(json.loads(line))
            return rows
        except Exception as exc:  # noqa: BLE001
            logger.warning("ClickHouseAdapter.execute_raw_query: %s", exc)
            return []

    def execute_dml(self, query: str) -> bool:
        """Run INSERT/DELETE/DDL; return True only on HTTP 200."""
        if not self._connected:
            return False
        try:
            resp = self._request(params={"database": self._database}, data=query)
            if resp.status_code != 200:
                logger.warning(
                    "ClickHouseAdapter.execute_dml HTTP %s: %s",
                    resp.status_code,
                    (resp.text or "")[:300],
                )
                return False
            return True
        except Exception as exc:  # noqa: BLE001
            logger.warning("ClickHouseAdapter.execute_dml: %s", exc)
            return False


class InMemoryTimeSeriesDB(TimeSeriesDBPort):
    """In-memory time-series DB for testing/fallback."""

    def __init__(self) -> None:
        self._data: dict[str, list[dict]] = {}
        self._connected = True

    def connect(self) -> bool:
        self._connected = True
        return True

    def disconnect(self) -> None:
        self._connected = False

    def write_ohlcv(self, symbol: str, timeframe: str, data: list[TimeSeriesPoint]) -> int:
        key = f"{symbol}_{timeframe}"
        if key not in self._data:
            self._data[key] = []

        for point in data:
            self._data[key].append({
                "timestamp": point.timestamp,
                "open": point.open,
                "high": point.high,
                "low": point.low,
                "close": point.close,
                "volume": point.volume,
            })

        return len(data)

    def query_ohlcv(
        self,
        symbol: str,
        timeframe: str,
        start_date: str,
        end_date: str,
        limit: int = 1000,
    ) -> list[dict[str, Any]]:
        key = f"{symbol}_{timeframe}"
        return self._data.get(key, [])[:limit]

    def execute_raw_query(self, query: str) -> list[dict[str, Any]]:
        return []
