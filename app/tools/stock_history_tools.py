from __future__ import annotations

"""Stock History Tools - 历史行情和K线相关工具."""


from typing import Any

from langchain_core.tools import tool
from pydantic import BaseModel, ConfigDict, Field

from app.core.logger import get_logger
from app.domain.enums import MarketCode

logger = get_logger(__name__)


class KlineChartToolResult(BaseModel):
    model_config = ConfigDict(extra="ignore")

    ticker: str
    period: str
    ok: bool = True
    error: str | None = None
    chart_url: str = ""
    evidence: str = ""
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)


class QlibFactorSnapshotToolResult(BaseModel):
    model_config = ConfigDict(extra="ignore")

    ticker: str
    period: str
    ok: bool = True
    error: str | None = None
    factors: dict[str, Any] = Field(default_factory=dict)
    evidence: str = ""
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)


class TickerProbeToolResult(BaseModel):
    model_config = ConfigDict(extra="ignore")

    ticker: str
    period: str
    ok: bool = True
    error: str | None = None
    price: float | None = None
    change_pct: float | None = None
    volume: int | None = None
    timestamp: str = ""
    evidence: str = ""
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)


class ChipDistributionToolResult(BaseModel):
    model_config = ConfigDict(extra="ignore")

    ticker: str
    ok: bool = True
    error: str | None = None
    distribution: dict[str, Any] = Field(default_factory=dict)
    evidence: str = ""
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)


@tool
def get_kline_chart(ticker: str, period: str = "1y") -> KlineChartToolResult:
    """获取股票K线图表URL."""
    from ..application.services.tool_facade_service import get_tool_facade_service

    try:
        service = get_tool_facade_service()
        chart_url = service.get_kline_chart_url(ticker, period=period)
        return KlineChartToolResult(
            ticker=ticker,
            period=period,
            chart_url=chart_url,
            evidence=f"Generated chart URL for {ticker}",
            confidence=0.8,
        )
    except Exception as e:
        logger.error(f"get_kline_chart failed: {e}")
        return KlineChartToolResult(
            ticker=ticker,
            period=period,
            ok=False,
            error=str(e),
            confidence=0.3,
        )


@tool
def get_qlib_factor_snapshot(ticker: str, period: str = "2y") -> QlibFactorSnapshotToolResult:
    """获取Qlib因子快照 (MA5/RET1/close)."""
    try:
        from ..infrastructure.providers.qlib_data import QlibDataProxy
    except ImportError:
        return QlibFactorSnapshotToolResult(
            ticker=ticker,
            period=period,
            ok=False,
            error="qlib_data module unavailable",
            confidence=0.1,
        )

    try:
        qlib = QlibDataProxy()
        fields = ["$close", "$return", "MA5"]
        df = qlib.get_factor_data(ticker, fields=fields, period=period)
        if df is not None and not df.empty:
            factors = {
                "latest_close": float(df["$close"].iloc[-1]) if "$close" in df.columns else None,
                "latest_return": float(df["$return"].iloc[-1]) if "$return" in df.columns else None,
                "ma5": float(df["MA5"].iloc[-1]) if "MA5" in df.columns else None,
                "data_points": len(df),
            }
            evidence = f"Retrieved {len(df)} data points for {ticker}"
            confidence = 0.9
        else:
            factors = {}
            evidence = f"No qlib data available for {ticker}"
            confidence = 0.3

        return QlibFactorSnapshotToolResult(
            ticker=ticker,
            period=period,
            factors=factors,
            evidence=evidence,
            confidence=confidence,
        )
    except Exception as e:
        logger.error(f"get_qlib_factor_snapshot failed: {e}")
        return QlibFactorSnapshotToolResult(
            ticker=ticker,
            period=period,
            ok=False,
            error=str(e),
            confidence=0.2,
        )


@tool
def probe_ticker(ticker: str, period: str = "5d") -> TickerProbeToolResult:
    """探测股票实时行情."""
    from ..domain.enums import MarketCode
    from ..infrastructure.providers.market_data import MultiSourceMarketProvider

    try:
        market = MarketCode.CN
        provider = MultiSourceMarketProvider()
        quotes = provider.get_realtime_quotes([ticker], market=market)

        if quotes:
            quote = quotes[0]
            return TickerProbeToolResult(
                ticker=ticker,
                period=period,
                price=quote.price,
                change_pct=quote.change_pct,
                volume=quote.volume,
                timestamp=quote.updated_at or "",
                evidence=f"Retrieved real-time quote: {quote.price}",
                confidence=0.9,
            )
        return TickerProbeToolResult(
            ticker=ticker,
            period=period,
            ok=False,
            error="No quote available",
            confidence=0.3,
        )
    except Exception as e:
        logger.error(f"probe_ticker failed: {e}")
        return TickerProbeToolResult(
            ticker=ticker,
            period=period,
            ok=False,
            error=str(e),
            confidence=0.2,
        )


@tool
def get_chip_distribution(ticker: str) -> ChipDistributionToolResult:
    """获取筹码分布数据."""
    from ..application.services.tool_facade_service import get_tool_facade_service

    try:
        service = get_tool_facade_service()
        dist = service.get_chip_distribution(ticker)
        return ChipDistributionToolResult(
            ticker=ticker,
            distribution=dist,
            evidence=f"Retrieved chip distribution for {ticker}",
            confidence=0.7,
        )
    except Exception as e:
        logger.error(f"get_chip_distribution failed: {e}")
        return ChipDistributionToolResult(
            ticker=ticker,
            ok=False,
            error=str(e),
            confidence=0.3,
        )


def infer_market_and_symbol(ticker: str) -> tuple[MarketCode, str]:
    """从ticker推断市场和标准化的symbol."""
    from ..domain.enums import MarketCode
    from ..infrastructure.mappers.symbol_normalizer import SymbolNormalizer

    ticker = ticker.strip().upper()
    if ticker.startswith("6"):
        return MarketCode.CN, ticker
    if ticker.startswith(("3", "0")):
        return MarketCode.CN, ticker
    if ticker.startswith("HK"):
        return MarketCode.HK, ticker
    if ticker.startswith("9"):
        return MarketCode.BJ, ticker
    return MarketCode.CN, SymbolNormalizer().normalize(ticker)


def _confidence_from_bars(n: int) -> float:
    """根据数据点数量计算置信度."""
    if n >= 60:
        return 0.95
    if n >= 20:
        return 0.8
    if n >= 5:
        return 0.6
    return 0.4


class TdxLocalSnapshotToolResult(BaseModel):
    model_config = ConfigDict(extra="ignore")
    ticker: str
    ok: bool = True
    error: str | None = None
    snapshot: dict[str, Any] = Field(default_factory=dict)
    evidence: str = ""
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)


@tool
def get_tdx_local_snapshot(ticker: str) -> TdxLocalSnapshotToolResult:
    """获取本地通达信离线数据摘要 (lday日线尾部、板块归属、股本变迁)."""
    from ..infrastructure.providers.tdx_file_adapter import TDXFileHistoryAdapter
    from ..infrastructure.tdx_local.paths import resolve_tdx_root

    try:
        from app.core.runtime_config import get_runtime
        tdx_path = get_runtime("TDX_ROOT_PATH", "")
        tdx_root = resolve_tdx_root(tdx_path if tdx_path else None)
        adapter = TDXFileHistoryAdapter(tdx_root=tdx_root)
        market, symbol = infer_market_and_symbol(ticker)

        lday_data = adapter.read_day(ticker=symbol, market=market.value)
        latest = lday_data[-5:] if len(lday_data) >= 5 else lday_data

        snapshot = {
            "symbol": symbol,
            "total_days": len(lday_data),
            "latest": latest,
            "last_date": lday_data[-1].get("date") if lday_data else None,
        }

        return TdxLocalSnapshotToolResult(
            ticker=ticker,
            snapshot=snapshot,
            evidence=f"Retrieved {len(lday_data)} days from local TDX",
            confidence=0.9,
        )
    except Exception as e:
        logger.error(f"get_tdx_local_snapshot failed: {e}")
        return TdxLocalSnapshotToolResult(
            ticker=ticker,
            ok=False,
            error=str(e),
            confidence=0.3,
        )
