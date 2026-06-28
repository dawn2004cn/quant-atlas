from __future__ import annotations
"""Quant Tools - LangGraph可调用量化工具入口.

此模块作为工具入口，将功能模块化拆分到:
- stock_history_tools: 历史行情和K线
- backtest_tools: 回测相关
- financial_tools: 财务数据
- news_tools: 新闻和情绪分析
- selection_tools: 选股和自选股
- pipeline_tools: 研究Pipeline
"""


from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, TypeVar

from pydantic import BaseModel, ConfigDict, Field
from langchain_core.tools import tool

from app.modules.market_data.services.watchlist_service import WatchlistApplicationService
from ..core.logger import get_logger
from ..domain.enums import MarketCode
from ..domain.ports import UserRepository, WebSearchProvider


logger = get_logger(__name__)

TResult = TypeVar("TResult", bound=BaseModel)


class MarketDataToolResult(BaseModel):
    model_config = ConfigDict(extra="ignore")
    ticker: str
    market: str
    period: str
    interval: str
    ok: bool = True
    error: str | None = None
    bars: list[dict[str, Any]] = Field(default_factory=list)
    bar_count: int = 0
    evidence: str = ""
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)


class Condition(BaseModel):
    field: str
    operator: str
    value: float


class ScreeningRule(BaseModel):
    operator: str = "AND"
    conditions: list[Condition] = Field(default_factory=list)


class ScreeningCriteria(BaseModel):
    rules: list[ScreeningRule] = Field(default_factory=list)
    top_n: int = Field(default=10, ge=1, le=500)


class StockSelectorArgs(BaseModel):
    model_config = ConfigDict(protected_namespaces=(), extra="forbid")
    model_name: str
    criteria: dict[str, Any] | None = None
    screening_criteria: ScreeningCriteria | None = None


@dataclass
class QuantToolRuntime:
    market_service: Any
    stock_service: Any
    watchlist_service: WatchlistApplicationService
    user_repository: UserRepository
    web_search_provider: WebSearchProvider | None = None
    qlib_pipeline_service: Any | None = None
    enable_qlib: bool = False
    rdagent_run_service: Any | None = None
    enable_rd_agent: bool = False
    basic_market_data_service: Any | None = None
    tdx_root_path: str | None = None


_RT: QuantToolRuntime | None = None


def configure_quant_tools(runtime: QuantToolRuntime) -> None:
    global _RT
    _RT = runtime


def reset_quant_tools_runtime() -> None:
    global _RT
    _RT = None


def _runtime() -> QuantToolRuntime:
    if _RT is None:
        raise RuntimeError("Quant tools not configured: call configure_quant_tools() from bootstrap.")
    return _RT


def _log_tool_exception(tool_name: str, exc: BaseException) -> str:
    logger.error(f"Tool '{tool_name}' failed: {exc}", exc_info=True)
    return f"Error: {type(exc).__name__}: {exc}"


def _guard_tool_call(tool_name: str, fn: Callable[[], TResult]) -> TResult:
    try:
        return fn()
    except Exception as e:
        logger.error(f"Tool '{tool_name}' failed: {e}")
        error_result = MarketDataToolResult(ticker="", market="", period="", interval="", ok=False, error=str(e))
        return error_result


from .stock_history_tools import (
    get_kline_chart,
    get_qlib_factor_snapshot,
    probe_ticker,
    get_chip_distribution,
    get_tdx_local_snapshot,
    infer_market_and_symbol as _infer_market_and_symbol,
    _confidence_from_bars as _conf_bars,
)

from .backtest_tools import (
    run_backtest,
    batch_backtest_selection,
    run_qlib_unified_backtest,
)

from .financial_tools import (
    get_cn_financial_statements,
    get_cn_research_reports,
    get_tdx_financial_data,
    get_cn_longhu_for_symbol,
)

from .news_tools import (
    get_stock_news,
    get_news_sentiment,
    get_market_mood,
)

from .selection_tools import (
    stock_selector,
    get_user_watchlist,
)

from .pipeline_tools import (
    get_research_pipeline_status,
    run_intelligent_pipeline,
    search_web_intelligence,
    get_yanbao_market_digest,
)


def infer_market_and_symbol(ticker: str) -> tuple[MarketCode, str]:
    return _infer_market_and_symbol(ticker)


def _confidence_from_bars(n: int) -> float:
    return _conf_bars(n)


@tool
def get_market_data(
    ticker: str,
    period: str = "1y",
    interval: str = "1d",
) -> MarketDataToolResult:
    """获取股票历史K线数据 (多数据源优先级)."""
    from ..infrastructure.providers.market_data import MultiSourceMarketProvider
    from datetime import datetime, timedelta

    market, symbol = infer_market_and_symbol(ticker)
    provider = MultiSourceMarketProvider()

    try:
        end_date = datetime.now().strftime("%Y-%m-%d")
        if period.endswith("d"):
            start_date = (datetime.now() - timedelta(days=int(period[:-1]))).strftime("%Y-%m-%d")
        elif period.endswith("y"):
            start_date = (datetime.now() - timedelta(days=int(period[:-1]) * 365)).strftime("%Y-%m-%d")
        else:
            start_date = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")

        bars = provider.get_stock_history(symbol, market, start_date, end_date)
        confidence = _confidence_from_bars(len(bars))

        return MarketDataToolResult(
            ticker=ticker,
            market=market.value,
            period=period,
            interval=interval,
            bars=bars,
            bar_count=len(bars),
            evidence=f"Retrieved {len(bars)} bars from market data provider",
            confidence=confidence,
        )
    except Exception as e:
        logger.error(f"get_market_data failed: {e}")
        return MarketDataToolResult(
            ticker=ticker,
            market=market.value,
            period=period,
            interval=interval,
            ok=False,
            error=str(e),
            confidence=0.3,
        )


QUANT_TOOL_BINDINGS = [
    get_market_data,
    get_kline_chart,
    get_qlib_factor_snapshot,
    probe_ticker,
    get_chip_distribution,
    get_tdx_local_snapshot,
    run_backtest,
    batch_backtest_selection,
    run_qlib_unified_backtest,
    get_cn_financial_statements,
    get_cn_research_reports,
    get_tdx_financial_data,
    get_cn_longhu_for_symbol,
    get_stock_news,
    get_news_sentiment,
    get_market_mood,
    stock_selector,
    get_user_watchlist,
    get_research_pipeline_status,
    run_intelligent_pipeline,
    search_web_intelligence,
    get_yanbao_market_digest,
]


def list_quant_tool_names() -> tuple[str, ...]:
    """Sorted unique LangChain tool names exposed to agents."""
    names: list[str] = []
    for binding in QUANT_TOOL_BINDINGS:
        name = getattr(binding, "name", None) or getattr(binding, "__name__", None)
        if name:
            names.append(str(name))
    return tuple(sorted(set(names)))


def quant_tools_agent_system_suffix() -> str:
    """Prompt fragment listing supported markets and callable tool names."""
    markets = "CN HK US CRYPTO"
    return f"{markets} " + " ".join(list_quant_tool_names())


QUANT_TOOLS_SUPERVISOR_PROMPT_FRAGMENT = """你是一个量化研究助手，可以调用以下工具获取股票数据:
- get_market_data: 获取历史K线
- get_stock_news: 获取新闻
- get_cn_financial_statements: 获取财务数据
- run_backtest: 执行回测
- stock_selector: 选股
等等...

当你需要获取数据时，直接调用对应工具。"""

__all__ = [
    "QUANT_TOOL_BINDINGS",
    "QUANT_TOOLS_SUPERVISOR_PROMPT_FRAGMENT",
    "list_quant_tool_names",
    "quant_tools_agent_system_suffix",
    "get_market_data",
    "get_kline_chart",
    "get_qlib_factor_snapshot",
    "probe_ticker",
    "get_chip_distribution",
    "run_backtest",
    "batch_backtest_selection",
    "run_qlib_unified_backtest",
    "get_cn_financial_statements",
    "get_cn_research_reports",
    "get_tdx_financial_data",
    "get_cn_longhu_for_symbol",
    "get_stock_news",
    "get_news_sentiment",
    "get_market_mood",
    "stock_selector",
    "get_user_watchlist",
    "get_research_pipeline_status",
    "run_intelligent_pipeline",
    "search_web_intelligence",
    "get_yanbao_market_digest",
    "configure_quant_tools",
    "QuantToolRuntime",
    "MarketDataToolResult",
    "ScreeningCriteria",
    "StockSelectorArgs",
]
