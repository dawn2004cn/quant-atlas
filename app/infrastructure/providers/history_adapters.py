from __future__ import annotations

"""Market Data Source Adapters - 多数据源适配器."""


import time
from datetime import date
from typing import Any

from ...config import INSTANCE_DIR
from ...core.logger import get_logger
from ...domain.enums import MarketCode

logger = get_logger(__name__)

_CIRCUIT_BREAKER_COOLDOWN = 300  # 5 minutes
_circuit_failures: dict[str, int] = {}
_circuit_until: dict[str, float] = {}


class MySQLHistoryAdapter:
    """MySQL 历史数据适配器 — 经 TdxDaykWritePort 读 stock_history_* 分表."""

    def get_history(self, symbol: str, market: MarketCode, start_date: date, end_date: date) -> list[dict]:
        if market != MarketCode.CN:
            return []
        try:
            from ...config import get_settings
            from ...infrastructure.repositories.deps import create_tdx_dayk_repository

            settings = get_settings()
            if not settings.use_mysql:
                return []
            repo = create_tdx_dayk_repository(settings)
            if repo is None:
                return []

            start_str = start_date.strftime("%Y-%m-%d") if start_date else None
            end_str = end_date.strftime("%Y-%m-%d") if end_date else None
            rows = repo.fetch_history_rows_for_code(
                symbol,
                start_date=start_str,
                end_date=end_str,
            )
            if rows:
                logger.info("MySQL got %d bars for %s", len(rows), symbol)
                return [
                    {
                        "date": str(r.get("date") or "")[:10],
                        "open": float(r.get("open") or 0),
                        "high": float(r.get("high") or 0),
                        "low": float(r.get("low") or 0),
                        "close": float(r.get("close") or 0),
                        "volume": float(r.get("volume") or 0),
                        "amount": float(r.get("amount") or 0),
                    }
                    for r in rows
                    if r.get("date")
                ]
        except Exception as e:
            logger.debug("MySQL miss: %s", e)
        return []


class TimescaleHistoryAdapter:
    """TimescaleDB ``market_bars`` 时序表（需 ``USE_TIMESCALEDB=1``）。"""

    def get_history(self, symbol: str, market: MarketCode, start_date: date, end_date: date) -> list[dict]:
        if market != MarketCode.CN:
            return []
        try:
            from ...config import get_settings
            from ...domain.shared.symbol_normalizer import SymbolNormalizer
            from ...infrastructure.repositories.deps import create_timescale_bar_repository
            from ...infrastructure.repositories.postgres.postgres_timescale_bar_repository import (
                NullPostgresTimescaleBarRepository,
            )

            settings = get_settings()
            if not settings.use_timescaledb:
                return []
            repo = create_timescale_bar_repository(settings)
            if isinstance(repo, NullPostgresTimescaleBarRepository):
                return []

            code = SymbolNormalizer.to_db_code(symbol, market="CN")
            start_str = start_date.strftime("%Y-%m-%d") if start_date else None
            end_str = end_date.strftime("%Y-%m-%d") if end_date else None
            rows = repo.get_bars(
                symbol=code,
                market="CN",
                start=start_str,
                end=end_str,
                limit=10000,
            )
            if not rows:
                return []
            out: list[dict] = []
            for r in rows:
                t = r.get("time")
                if hasattr(t, "strftime"):
                    ds = t.strftime("%Y-%m-%d")
                else:
                    ds = str(t)[:10]
                if not ds:
                    continue
                out.append(
                    {
                        "date": ds,
                        "open": float(r.get("open") or 0),
                        "high": float(r.get("high") or 0),
                        "low": float(r.get("low") or 0),
                        "close": float(r.get("close") or 0),
                        "volume": float(r.get("volume") or 0),
                        "amount": float(r.get("amount") or 0),
                    }
                )
            logger.info("TimescaleDB got %d bars for %s", len(out), symbol)
            return out
        except Exception as e:
            logger.debug("TimescaleDB miss: %s", e)
        return []


class SqliteHistoryAdapter:
    """SQLite本地历史数据适配器."""

    def get_history(self, symbol: str, market: MarketCode, start_date: date, end_date: date) -> list[dict]:
        try:
            from ...config import INSTANCE_DIR
            from ...infrastructure.database.adapters import SqliteAdapter
            from ...infrastructure.database.history_repository import HistoryRepository

            db_path = INSTANCE_DIR / "stock_cache.db"
            if not db_path.exists():
                return []

            db_adapter = SqliteAdapter(str(db_path))
            repo = HistoryRepository(db_adapter)

            start_str = start_date.isoformat() if start_date else "2000-01-01"
            end_str = end_date.isoformat() if end_date else "2099-12-31"

            rows = repo.get_history(symbol, start_str, end_str, limit=5000)
            if rows:
                logger.info(f"SQLite got {len(rows)} bars for {symbol}")
                return rows
        except Exception as e:
            logger.debug(f"SQLite history miss: {e}")
        return []


class QlibBinAdapter:
    """qlib_bin本地数据适配器."""

    def get_history(self, symbol: str, market: MarketCode, start_date: date, end_date: date) -> list[dict]:
        try:
            from ...infrastructure.providers.qlib_history_provider import QlibHistoryProvider
            provider = QlibHistoryProvider(provider_uri="file://" + str(INSTANCE_DIR / "qlib_bin"))
            df = provider.get_history(symbol, market, start_date, end_date)
            if df is not None and not df.empty:
                logger.info(f"qlib_bin got {len(df)} bars for {symbol}")
                return df.to_dict("records")
        except Exception as e:
            logger.debug(f"qlib_bin miss: {e}")
        return []


class TdxFileAdapter:
    """通达信lday文件适配器."""

    _instance = None

    def __init__(self, tdx_root: str | None = None):
        from ...infrastructure.tdx_local.paths import resolve_tdx_root
        self._root = tdx_root if tdx_root else None
        if self._root is None:
            try:
                self._root = resolve_tdx_root(None)
            except Exception:
                self._root = None

    def _get_adapter(self):
        if TdxFileAdapter._instance is None:
            from ...infrastructure.providers.tdx_file_adapter import TDXFileHistoryAdapter
            TdxFileAdapter._instance = TDXFileHistoryAdapter(tdx_root=self._root)
        return TdxFileAdapter._instance

    def get_history(self, symbol: str, market: MarketCode, start_date: date, end_date: date) -> list[dict]:
        try:
            adapter = self._get_adapter()
            start_str = start_date.strftime("%Y-%m-%d") if start_date else "1990-01-01"
            end_str = end_date.strftime("%Y-%m-%d") if end_date else "2099-12-31"
            return adapter.get_stock_history(symbol, market, start_str, end_str)
        except Exception as e:
            logger.debug(f"TDX file miss: {e}")
        return []


class AkshareAdapter:
    """东财AkShare前复权数据适配器."""

    def get_history(self, symbol: str, market: MarketCode, start_date: date, end_date: date) -> list[dict]:
        try:
            from ...infrastructure.providers.cn_akshare_history import fetch_cn_daily_qfq
            start_str = start_date.strftime("%Y-%m-%d") if start_date else "1990-01-01"
            end_str = end_date.strftime("%Y-%m-%d") if end_date else date.today().isoformat()
            bars, msg = fetch_cn_daily_qfq(symbol, start_str, end_str)
            if bars:
                logger.info(f"AkShare got {len(bars)} bars for {symbol}: {msg}")
                return bars
            else:
                logger.debug(f"AkShare returned empty: {msg}")
        except Exception as e:
            logger.debug(f"AkShare miss: {e}")
        return []


class TdxTcpAdapter:
    """通达信TCP连接适配器."""

    def get_history(self, symbol: str, market: MarketCode, start_date: date, end_date: date) -> list[dict]:
        try:
            from ...infrastructure.providers.cn_tdx_provider import TdxProvider
            provider = TdxProvider()
            return provider.get_history(symbol, market, start_date, end_date)
        except Exception as e:
            logger.debug(f"TDX TCP miss: {e}")
        return []


def _build_cn_history_adapters() -> list[tuple[str, Any]]:
    """CN 读链：时序库优先（可配置），MySQL 降为后备。"""
    from ...core.runtime_config import get_runtime_bool
    from ...infrastructure.database.timeseries_settings import (
        load_clickhouse_settings,
        load_questdb_settings,
    )
    from .timeseries_history_adapters import ClickHouseHistoryAdapter, QuestDBHistoryAdapter

    prefer_ts = get_runtime_bool("HISTORY_PREFER_TIMESERIES", True)
    tail: list[tuple[str, Any]] = [
        ("mysql", MySQLHistoryAdapter()),
        ("qlib", QlibBinAdapter()),
        ("tdx_file", TdxFileAdapter()),
        ("akshare", AkshareAdapter()),
        ("tdx_tcp", TdxTcpAdapter()),
        ("sqlite", SqliteHistoryAdapter()),
    ]
    if not prefer_ts:
        return [
            ("mysql", MySQLHistoryAdapter()),
            ("timescale", TimescaleHistoryAdapter()),
            ("questdb", QuestDBHistoryAdapter()),
            ("clickhouse", ClickHouseHistoryAdapter()),
            *tail[1:],
        ]

    head: list[tuple[str, Any]] = []
    if load_questdb_settings() is not None:
        head.append(("questdb", QuestDBHistoryAdapter()))
    if load_clickhouse_settings() is not None:
        head.append(("clickhouse", ClickHouseHistoryAdapter()))
    head.append(("timescale", TimescaleHistoryAdapter()))
    return head + tail


class MultiSourceHistoryProvider:
    """多数据源历史行情提供者 - 按优先级尝试各个数据源（含熔断）."""

    last_source: str | None = None

    def __init__(self) -> None:
        self._cn_adapters = _build_cn_history_adapters()
        self._default_adapters = [
            ("mysql", MySQLHistoryAdapter()),
            ("sqlite", SqliteHistoryAdapter()),
            ("qlib", QlibBinAdapter()),
            ("tdx_file", TdxFileAdapter()),
            ("tdx_tcp", TdxTcpAdapter()),
            ("akshare", AkshareAdapter()),
        ]

    def _adapters_for(self, market: MarketCode) -> list[tuple[str, Any]]:
        if market == MarketCode.CN:
            return self._cn_adapters
        return self._default_adapters

    def get_history(self, symbol: str, market: MarketCode, start_date: date, end_date: date) -> list[dict]:
        """按优先级尝试各个数据源，返回第一个成功的结果。失败 3 次后熔断 5 分钟."""
        self.last_source = None
        for name, adapter in self._adapters_for(market):
            if _circuit_until.get(name, 0) > time.time():
                continue
            try:
                result = adapter.get_history(symbol, market, start_date, end_date)
                if result:
                    _circuit_failures.pop(name, None)
                    _circuit_until.pop(name, None)
                    self.last_source = name
                    logger.info(f"Got history for {symbol} from {name}: {len(result)} bars")
                    return result
            except Exception as e:
                logger.debug(f"Adapter {name} failed: {e}")
                _circuit_failures[name] = _circuit_failures.get(name, 0) + 1
                if _circuit_failures[name] >= 3:
                    _circuit_until[name] = time.time() + _CIRCUIT_BREAKER_COOLDOWN
                    logger.warning(f"Adapter {name} circuit broken for {_CIRCUIT_BREAKER_COOLDOWN}s")
        return []


def get_multi_source_history_provider() -> MultiSourceHistoryProvider:
    """获取多数据源历史提供者单例."""
    return MultiSourceHistoryProvider()
