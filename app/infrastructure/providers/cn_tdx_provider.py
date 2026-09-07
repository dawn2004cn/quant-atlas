from __future__ import annotations

"""TDX 数据 Provider - 实时行情 + 历史数据"""


from datetime import datetime
from typing import Any

import pandas as pd

from ...core.logger import get_logger
from ...domain.enums import MarketCode
from ...domain.ports import HistoryPort
from ..tdx_local.lday_reader import _get_tdx_market_code, read_lday_file, read_lday_file_with_qfq
from ..tdx_local.paths import TdxLocalPaths, resolve_tdx_root_configured

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


def _as_date_str(value: Any) -> str:
    if hasattr(value, "strftime"):
        return value.strftime("%Y-%m-%d")
    text = str(value or "")[:10]
    return text


def _hq_bar_date(raw: dict[str, Any]) -> str:
    if raw.get("datetime"):
        return str(raw["datetime"])[:10]
    year, month, day = raw.get("year"), raw.get("month"), raw.get("day")
    if year and month and day:
        return f"{int(year):04d}-{int(month):02d}-{int(day):02d}"
    return ""


def tdx_rows_to_stock_quotes(rows: list[dict[str, Any]], market: MarketCode) -> list[Any]:
    """Map TDX HQ quote rows to StockQuote (same fields as TDX PC Level-1)."""
    from app.domain.shared.pytdx_quote_mapper import pytdx_row_to_quote_payload
    from app.domain.shared.value_objects import StockQuote

    quotes = []
    for raw in rows:
        payload = pytdx_row_to_quote_payload(raw)
        code = str(payload.get("code") or raw.get("code") or "")
        if not code:
            continue
        quotes.append(
            StockQuote(
                code=code,
                name=str(payload.get("name") or code),
                market=market,
                price=float(payload.get("price") or 0),
                change_pct=float(payload.get("change_pct") or 0),
                volume=float(payload.get("volume") or 0),
                amount=float(payload.get("amount") or 0),
                open_price=float(payload.get("open_price") or 0),
                high_price=float(payload.get("high_price") or 0),
                low_price=float(payload.get("low_price") or 0),
                source="tdx",
                updated_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                change_amount=float(payload.get("change_amount") or 0),
                prev_close=float(payload.get("prev_close") or 0),
                amplitude=float(payload.get("amplitude") or 0),
            )
        )
    return quotes


class TdxHistoryProvider(HistoryPort):
    """TDX 历史数据 Provider - 支持本地文件和 API"""

    def __init__(self, tdx_root_path: str | None = None, use_qfq: bool = True):
        self._tdx_root = resolve_tdx_root_configured(tdx_root_path)
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
        self._tdx_mgr = None

    def _get_manager(self):
        if self._tdx_mgr is None:
            try:
                from ..external.tdx_manager import TdxConnectionManager

                self._tdx_mgr = TdxConnectionManager()
            except Exception as e:
                logger.warning(f"TDX 连接失败: {e}")
                return None
        return self._tdx_mgr

    def get_quote(self, symbol: str, market: MarketCode = MarketCode.CN) -> dict[str, Any] | None:
        """获取单只股票实时行情"""
        rows = self.get_quotes([symbol], market)
        return rows[0] if rows else None

    def get_quotes(self, symbols: list[str], market: MarketCode = MarketCode.CN) -> list[dict[str, Any]]:
        """批量获取实时行情（通达信 HQ 单次最多 80 只，与 PC 端一致）。"""
        if not symbols:
            return []

        tdx = self._get_manager()
        if not tdx:
            return []

        pairs: list[tuple[int, str]] = []
        for symbol in symbols:
            prefix, _ = _symbol_to_market_code(symbol, market)
            pairs.append((_get_tdx_market_code(prefix), symbol[-6:]))

        quotes: list[dict[str, Any]] = []
        try:
            for i in range(0, len(pairs), 80):
                result = tdx.execute("get_security_quotes", pairs[i : i + 80])
                if not result:
                    continue
                for raw in result:
                    parsed = self._parse_quote(raw)
                    if parsed:
                        quotes.append(parsed)
        except Exception as e:
            logger.warning("获取实时行情失败: %s", e)
        return quotes

    def _parse_quote(self, raw: dict) -> dict[str, Any]:
        """解析 TDX 行情数据"""
        from app.domain.shared.pytdx_quote_mapper import pytdx_row_to_quote_payload

        payload = pytdx_row_to_quote_payload(raw)
        code = str(payload.get("code") or raw.get("code") or "")
        return {
            "symbol": code,
            "code": code,
            "name": payload.get("name") or raw.get("name", ""),
            "open": payload.get("open_price", raw.get("open", 0.0)),
            "high": payload.get("high_price", raw.get("high", 0.0)),
            "low": payload.get("low_price", raw.get("low", 0.0)),
            "close": payload.get("price", raw.get("price", raw.get("close", 0.0))),
            "price": payload.get("price", 0.0),
            "volume": payload.get("volume", raw.get("vol", 0)),
            "amount": payload.get("amount", 0.0),
            "bid1": raw.get("bid1", 0.0),
            "ask1": raw.get("ask1", 0.0),
            "bid_vol1": raw.get("bid_vol1", 0),
            "ask_vol1": raw.get("ask_vol1", 0),
            "change_pct": payload.get("change_pct", 0.0),
            "change_amount": payload.get("change_amount", 0.0),
            "prev_close": payload.get("prev_close", 0.0),
            "source": "tdx",
            "timestamp": datetime.now().isoformat(),
        }

    def is_connected(self) -> bool:
        """检查 TDX 连接状态"""
        tdx = self._get_manager()
        return tdx is not None and bool(getattr(tdx, "is_connected", False))


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
        market: MarketCode | str = MarketCode.CN,
        start: str = "2010-01-01",
        end: str | None = None,
    ) -> list[dict[str, Any]]:
        """获取历史数据：本地 vipdoc 优先，缺失时走 HQ（与通达信 PC 下载日线一致）。"""
        market_code = market if isinstance(market, MarketCode) else MarketCode.CN
        start_s = _as_date_str(start)
        end_s = _as_date_str(end or datetime.now())
        local = self._history.get_stock_history(symbol, market_code, start_s, end_s)
        if local:
            for row in local:
                row.setdefault("source", "tdx_file")
            return local
        return self._history_from_hq(symbol, market_code, start_s, end_s)

    def get_history(
        self,
        symbol: str,
        market: MarketCode | str = MarketCode.CN,
        start: Any = "2010-01-01",
        end: Any = None,
    ) -> list[dict[str, Any]]:
        """Alias used by history adapters and AsyncMarketProvider."""
        return self.get_stock_history(symbol, market, _as_date_str(start), _as_date_str(end) if end else None)

    def _history_from_hq(
        self,
        symbol: str,
        market: MarketCode,
        start: str,
        end: str,
    ) -> list[dict[str, Any]]:
        tdx = self._realtime._get_manager()
        if not tdx:
            return []
        prefix, _ = _symbol_to_market_code(symbol, market)
        market_id = _get_tdx_market_code(prefix)
        code = symbol[-6:]
        raw_rows: list[dict[str, Any]] = []
        try:
            offset = 0
            while offset < 8000:
                batch = tdx.execute("get_security_bars", 9, market_id, code, offset, 800)
                if not batch:
                    break
                raw_rows.extend(batch)
                if len(batch) < 800:
                    break
                offset += 800
        except Exception as exc:
            logger.warning("TDX HQ history failed %s: %s", symbol, exc)
            return []

        out: list[dict[str, Any]] = []
        for raw in raw_rows:
            ds = _hq_bar_date(raw)
            if not ds or ds < start or ds > end:
                continue
            out.append(
                {
                    "date": ds,
                    "open": float(raw.get("open") or 0),
                    "high": float(raw.get("high") or 0),
                    "low": float(raw.get("low") or 0),
                    "close": float(raw.get("close") or 0),
                    "volume": float(raw.get("vol") or raw.get("volume") or 0),
                    "amount": float(raw.get("amount") or 0),
                    "source": "tdx_hq",
                }
            )
        out.sort(key=lambda row: row["date"])
        return out

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
