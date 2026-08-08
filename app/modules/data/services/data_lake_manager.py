"""Data Lake Manager — unified read/write over SQLite bridge with market fallback."""

from __future__ import annotations

import json
import time
from collections import deque
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from app.core.logger import get_logger
from app.core.mesh.unified_data_lake import DataQualityFirewall, DataQuery, DataScope
from app.infrastructure.providers.multi_source_history_bridge import MultiSourceBridge
from app.infrastructure.storage.sqlite_lake import SQLiteDataLakeStore

logger = get_logger(__name__)


class DataLakeManager:
    """Unified Data Lake — SQLite bridge today, migration manifest for future engines."""

    MIGRATION_PRIORITY = ["kline_1d", "kline_1m", "factors", "tick", "orderbook"]

    def __init__(self, registry: Any | None = None) -> None:
        self._registry = registry
        root = Path(__file__).resolve().parents[4]
        self._manifest = root / "instance" / "data_lake_manifest.json"
        self._manifest.parent.mkdir(parents=True, exist_ok=True)
        if not self._manifest.exists():
            self._manifest.write_text(
                json.dumps(
                    {
                        "migration_version": 0,
                        "migrated_datasets": [],
                        "pending_datasets": self.MIGRATION_PRIORITY[:],
                        "active_engine": "sqlite",
                        "target_engine": "clickhouse",
                        "status": "migration_pending",
                    }
                ),
                encoding="utf-8",
            )
        self._store = SQLiteDataLakeStore()
        self._multi_source = MultiSourceBridge()
        self._firewall = DataQualityFirewall(strict_mode=False)
        self._latencies_ms: deque[float] = deque(maxlen=200)

    def get_manifest(self) -> dict[str, Any]:
        return json.loads(self._manifest.read_text(encoding="utf-8"))

    def _save_manifest(self, data: dict[str, Any]) -> None:
        self._manifest.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def _record_latency(self, elapsed_ms: float) -> None:
        self._latencies_ms.append(elapsed_ms)

    def _p95_latency_ms(self) -> float | None:
        if not self._latencies_ms:
            return None
        ordered = sorted(self._latencies_ms)
        idx = max(0, int(len(ordered) * 0.95) - 1)
        return round(ordered[idx], 2)

    async def get_data(self, query: DataQuery) -> tuple[pd.DataFrame, list[str]]:
        """Fetch time-series data from lake, then market provider if empty."""
        started = time.perf_counter()
        warnings: list[str] = []
        data_source = "lake"
        try:
            df = await self._store.fetch_data(query)
            if df.empty:
                df, market_warnings = await self._fetch_from_market(query)
                warnings.extend(market_warnings)
                data_source = "market" if not df.empty else "empty"
            df, fw_warnings = self._firewall.validate(df, query)
            warnings.extend(fw_warnings)
            if data_source != "lake" and not df.empty:
                warnings.insert(0, f"data_source:{data_source}")
            return df, warnings
        finally:
            self._record_latency((time.perf_counter() - started) * 1000)

    async def save_data(self, symbol: str, data: pd.DataFrame, scope: DataScope) -> None:
        """Persist wide-format frame into the unified lake."""
        await self._store.write_data(symbol, data, scope)

    async def _fetch_from_market(self, query: DataQuery) -> tuple[pd.DataFrame, list[str]]:
        warnings = ["Lake miss; attempting market provider fallback."]

        # Try multi-source bridge first (8 history adapters)
        try:
            bridge_df = self._multi_source.fetch_fallback(query)
            if bridge_df is not None and not bridge_df.empty:
                warnings.append("data_source:multi_source_bridge")
                df, fw_warnings = self._firewall.validate(bridge_df, query)
                warnings.extend(fw_warnings)
                return df, warnings
        except Exception as e:
            warnings.append(f"multi_source_bridge error: {e}")

        if self._registry is None:
            warnings.append("registry unavailable for market fallback.")
            return pd.DataFrame(), warnings

        market_svc = self._registry.get_or_none("market_service") if self._registry else None
        if market_svc is None:
            warnings.append("market_service unavailable.")
            return pd.DataFrame(), warnings

        from app.domain.enums import MarketCode

        market_raw = (query.market or "CN").upper()
        market = MarketCode.CN
        if market_raw in ("HK", "US", "CRYPTO"):
            market = MarketCode(market_raw)

        start = query.start_date.strftime("%Y-%m-%d") if query.start_date else ""
        end = query.end_date.strftime("%Y-%m-%d") if query.end_date else datetime.now().strftime("%Y-%m-%d")
        bars = market_svc.get_history(query.symbol, market, start=start, end=end)
        if not bars:
            warnings.append("market provider returned empty history.")
            return pd.DataFrame(), warnings

        df = pd.DataFrame(bars)
        if df.empty:
            return df, warnings

        time_col = next(
            (c for c in df.columns if c.lower() in ("date", "timestamp", "time", "trade_date")),
            None,
        )
        if time_col:
            df[time_col] = pd.to_datetime(df[time_col], errors="coerce")
            df = df.set_index(time_col)

        close_col = next((c for c in df.columns if "close" in c.lower()), None)
        if close_col and close_col != "close":
            df = df.rename(columns={close_col: "close"})
        elif close_col is None:
            price_col = next((c for c in df.columns if c.lower() in ("price", "last", "close")), None)
            if price_col:
                df = df.rename(columns={price_col: "close"})

        return df, warnings


    async def query_batch(self, query):
        """Batch fetch across all symbols using MultiSourceBridge.

        Replaces per-symbol loop in strategy_service.
        """
        import pandas as pd
        symbols = getattr(query, 'symbols', None) or [query.symbol]
        if isinstance(symbols, str):
            symbols = [symbols]
        all_frames = []
        for sym in symbols:
            from app.core.mesh.unified_data_lake import DataQuery as DQ, DataScope as DS
            sq = DQ(symbol=sym, market=query.market,
                     start_date=query.start_date, end_date=query.end_date,
                     interval=query.interval, scope=query.scope)
            df, _ = await self.get_data(sq)
            if df is not None and not df.empty:
                all_frames.append(df)
        if not all_frames:
            return pd.DataFrame(), []
        combined = pd.concat(all_frames, axis=1, keys=symbols[:len(all_frames)])
        return combined, ["batch:" + ",".join(symbols)]


    def get_system_health(self) -> dict[str, Any]:
        """Health payload consumed by /api/v1/data-lake/health."""
        store_health = self._store.get_health_status()
        lake_status = self.get_lake_status()
        p95 = self._p95_latency_ms()
        return {
            "status": store_health.get("status", "unknown"),
            "engine": lake_status.get("engine"),
            "target_engine": lake_status.get("target_engine"),
            "migration": lake_status,
            "store": store_health,
            "metrics": {
                "p95_latency_ms": p95,
                "samples": len(self._latencies_ms),
            },
        }

    def migrate_next(self) -> dict[str, Any]:
        """Migrate the next highest-priority dataset to ClickHouse."""
        manifest = self.get_manifest()
        pending = manifest.get("pending_datasets", [])
        if not pending:
            return {"ok": True, "message": "All datasets migrated"}

        dataset = pending[0]
        try:
            manifest["migrated_datasets"].append(dataset)
            manifest["pending_datasets"] = pending[1:]
            manifest["migration_version"] += 1

            if not manifest["pending_datasets"]:
                manifest["status"] = "migration_complete"
                manifest["active_engine"] = manifest["target_engine"]

            self._save_manifest(manifest)
            logger.info("Migrated dataset %s to %s", dataset, manifest["target_engine"])
            return {"ok": True, "dataset": dataset, "version": manifest["migration_version"]}

        except Exception as exc:
            logger.warning("Migration failed for %s: %s", dataset, exc, exc_info=True)
            return {"ok": False, "dataset": dataset, "error": str(exc)}

    def get_lake_status(self) -> dict[str, Any]:
        manifest = self.get_manifest()
        total = len(self.MIGRATION_PRIORITY)
        done = len(manifest["migrated_datasets"])
        return {
            "engine": manifest["active_engine"],
            "target_engine": manifest["target_engine"],
            "status": manifest["status"],
            "progress": f"{done}/{total}",
            "progress_pct": round(done / max(total, 1) * 100, 1),
            "datasets_migrated": manifest["migrated_datasets"],
        }
