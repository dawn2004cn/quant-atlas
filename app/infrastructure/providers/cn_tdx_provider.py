from __future__ import annotations
"""TDX 数据 Provider - 实时行情 + 历史数据"""


from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from ...core.logger import get_logger
from ...domain.enums import MarketCode
from ...domain.ports import HistoryPort
from ..external.tdx_manager import TdxConnectionManager
from ..tdx_local.lday_reader import read_lday_file, read_lday_file_with_qfq, _get_tdx_market_code
from ..tdx_local.paths import TdxLocalPaths, resolve_tdx_root

logger = get_logger(__name__)


def _symbol_to_market_code(symbol: str, market: MarketCode = MarketCode.CN) -> tuple[str, str]:
    """将股票代码转换为市场前缀和市场代码。支持 sh600519 / sz000001 / 600519 格式。"""
    s = symbol.lower()
    if s.startswith(("sh", "6")):
        return "sh", "sh"
    if s.startswith(("sz", "0", "3")):
        return "sz", "sz"
    if s.startswith(("bj", "4", "9", "8")):
        return "bj", "bj"
    return "sz", "sz"


class TdxHistoryProvider(HistoryPort):
    """TDX 历史数据 Provider - 支持本地文件和 API"""

    def __init__(self, tdx_root_path: str | None = None, use_qfq: bool = True):
        self._tdx_root = resolve_tdx_root(tdx_root_path)
        self._paths = TdxLocalPaths(self._tdx_root) if self._tdx_root else None
        self._use_qfq = use_qfq
        self._cache: dict[str, pd.DataFrame] = {}

    def get_stock_history(
        self,
        symbol: str,
        market: MarketCode,
        start: str,
        end: str,
    ) -> list[dict[str, Any]]:
        """获取历史 K 线数据"""
        df = self._read_to_dataframe(symbol, market)
        if df is None or df.empty:
            return []

        df = df.copy()
        df["date"] = pd.to_datetime(df["date"])
        start_dt = pd.to_datetime(start)
        end_dt = pd.to_datetime(end)

        filtered = df[(df["date"] >= start_dt) & (df["date"] <= end_dt)]
        filtered = filtered.sort_values("date")
        return filtered.to_dict(orient="records")

    def _read_to_dataframe(self, symbol: str, market: MarketCode) -> pd.DataFrame | None:
        """读取 TDX 文件到 DataFrame"""
        cache_key = f"{market.value}:{symbol}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        if not self._paths:
            return None

        market_prefix, market_str = _symbol_to_market_code(symbol, market)
        file_path = self._paths.lday_file_by_market(market=market_prefix, code6=symbol)

        if not file_path.is_file():
            logger.warning(f"TDX 文件不存在: {file_path}")
            return None

        if self._use_qfq:
            rows = read_lday_file_with_qfq(file_path, market=market_prefix, code=symbol)
        else:
            rows = read_lday_file(file_path)

        if not rows:
            return None

        df = pd.DataFrame(rows)
        df["date"] = pd.to_datetime(df["date"])
        self._cache[cache_key] = df
        return df

    def get_symbols_list(self, market: MarketCode = MarketCode.CN) -> list[str]:
        """获取 TDX 目录中所有股票代码"""
        if not self._paths:
            return []

        symbols = []
        for market_str in ["sh", "sz", "bj"]:
            lday_dir = self._paths.vipdoc / market_str / "lday"
            if not lday_dir.is_dir():
                continue
            for f in lday_dir.glob("*.day"):
                code = f.stem
                code6 = code[-6:] if len(code) >= 6 else code
                if len(code6) == 6 and code6.isdigit():
                    symbols.append(f"{market_str}{code6}")
        return sorted(symbols)

    def clear_cache(self) -> None:
        """清除缓存"""
        self._cache.clear()


class TdxRealTimeProvider:
    """TDX 实时行情 Provider"""

    def __init__(self):
        self._tdx_mgr: TdxConnectionManager | None = None

    def _get_manager(self) -> TdxConnectionManager | None:
        if self._tdx_mgr is None:
            try:
                self._tdx_mgr = TdxConnectionManager()
            except Exception as e:
                logger.warning(f"TDX 连接失败: {e}")
                return None
        return self._tdx_mgr

    def get_quote(self, symbol: str, market: MarketCode = MarketCode.CN) -> dict[str, Any] | None:
        """获取单只股票实时行情"""
        tdx = self._get_manager()
        if not tdx:
            return None

        market_code = _get_tdx_market_code(_symbol_to_market_code(symbol, market)[0])
        code = symbol[-6:]

        try:
            result = tdx.execute("get_security_quotes", [(market_code, code)])
            if result and len(result) > 0:
                return self._parse_quote(result[0])
        except Exception as e:
            logger.warning(f"获取实时行情失败 {symbol}: {e}")
        return None

    def get_quotes(self, symbols: list[str], market: MarketCode = MarketCode.CN) -> list[dict[str, Any]]:
        """批量获取实时行情"""
        if not symbols:
            return []

        tdx = self._get_manager()
        if not tdx:
            return []

        quotes = []
        for symbol in symbols:
            quote = self.get_quote(symbol, market)
            if quote:
                quote["symbol"] = symbol
                quotes.append(quote)
        return quotes

    def _parse_quote(self, raw: dict) -> dict[str, Any]:
        """解析 TDX 行情数据"""
        return {
            "symbol": raw.get("code", ""),
            "name": raw.get("name", ""),
            "open": raw.get("open", 0.0),
            "high": raw.get("high", 0.0),
            "low": raw.get("low", 0.0),
            "close": raw.get("price", raw.get("close", 0.0)),
            "volume": raw.get("vol", 0),
            "amount": raw.get("amount", 0.0),
            "bid1": raw.get("bid1", 0.0),
            "ask1": raw.get("ask1", 0.0),
            "bid_vol1": raw.get("bid_vol1", 0),
            "ask_vol1": raw.get("ask_vol1", 0),
            "timestamp": datetime.now().isoformat(),
        }

    def is_connected(self) -> bool:
        """检查 TDX 连接状态"""
        tdx = self._get_manager()
        return tdx is not None and getattr(tdx, "is_connected", False)


class TdxDataProvider:
    """TDX 综合数据 Provider - 整合实时 + 历史"""

    def __init__(self, tdx_root_path: str | None = None, use_qfq: bool = True):
        self._history = TdxHistoryProvider(tdx_root_path, use_qfq)
        self._realtime = TdxRealTimeProvider()

    @property
    def history(self) -> TdxHistoryProvider:
        return self._history

    @property
    def realtime(self) -> TdxRealTimeProvider:
        return self._realtime

    def get_stock_history(
        self,
        symbol: str,
        market: MarketCode = MarketCode.CN,
        start: str = "2010-01-01",
        end: str | None = None,
    ) -> list[dict[str, Any]]:
        """获取历史数据"""
        end = end or datetime.now().strftime("%Y-%m-%d")
        return self._history.get_stock_history(symbol, market, start, end)

    def get_quote(self, symbol: str, market: MarketCode = MarketCode.CN) -> dict[str, Any] | None:
        """获取实时行情"""
        return self._realtime.get_quote(symbol, market)

    def get_quotes(self, symbols: list[str], market: MarketCode = MarketCode.CN) -> list[dict[str, Any]]:
        """批量获取实时行情"""
        return self._realtime.get_quotes(symbols, market)

    def is_realtime_connected(self) -> bool:
        """检查实时行情连接状态"""
        return self._realtime.is_connected()

    def get_all_symbols(self, market: MarketCode = MarketCode.CN) -> list[str]:
        """获取所有可用股票代码"""
        return self._history.get_symbols_list(market)


def create_tdx_provider(
    tdx_root_path: str | None = None,
    use_qfq: bool = True,
) -> TdxDataProvider:
    """创建 TDX Provider 实例"""
    return TdxDataProvider(tdx_root_path=tdx_root_path, use_qfq=use_qfq)