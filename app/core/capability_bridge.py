"""Bridge existing QuantToolRuntime tools into the CapabilityRegistry.

Phase 5.2 — auto-registers LangChain @tool bindings as discoverable
capabilities so AI agents can find tools by semantic query instead of
hardcoded references.
"""

from __future__ import annotations

import logging
from typing import Any

from app.core.capability_registry import (
    CapabilityRegistry,
    get_capability_registry,
)

logger = logging.getLogger(__name__)

# ── semantic metadata for existing tools ──────────────────────────────────

_TOOL_SEMANTICS: dict[str, dict[str, Any]] = {
    "get_market_data": {
        "description": "获取A股/港股/美股历史K线数据，支持日线/周线/分钟线",
        "domain": "market_data",
        "tags": ["kline", "history", "market", "realtime"],
    },
    "get_kline_chart": {
        "description": "获取股票K线图数据，包含OHLCV和技术指标",
        "domain": "market_data",
        "tags": ["kline", "chart", "technical"],
    },
    "get_qlib_factor_snapshot": {
        "description": "获取Qlib量化因子快照数据",
        "domain": "market_data",
        "tags": ["factor", "qlib", "quantitative"],
    },
    "probe_ticker": {
        "description": "探测股票代码有效性，获取实时行情概览",
        "domain": "market_data",
        "tags": ["probe", "quote", "realtime"],
    },
    "get_realtime_quote": {
        "description": "获取股票实时行情（A股交易时段优先 TDX→Redis）。",
        "domain": "market_data",
        "tags": ["tdx", "redis", "quote", "realtime"],
    },
    "get_stock_history_bars": {
        "description": "获取股票历史 K 线 bars（交易时段：lday + Redis 实时合成当日 bar）。",
        "domain": "market_data",
        "tags": ["kline", "history", "bars", "tdx"],
    },
    "get_chip_distribution": {
        "description": "获取股票筹码分布数据，分析持仓成本结构",
        "domain": "market_data",
        "tags": ["chip", "distribution", "cost"],
    },
    "get_tdx_local_snapshot": {
        "description": "获取通达信本地数据快照",
        "domain": "market_data",
        "tags": ["tdx", "local", "snapshot"],
    },
    "run_backtest": {
        "description": "执行单只股票的量化回测策略",
        "domain": "backtest",
        "tags": ["backtest", "strategy", "performance"],
    },
    "batch_backtest_selection": {
        "description": "批量回测选股策略，对比多只股票表现",
        "domain": "backtest",
        "tags": ["backtest", "batch", "screening"],
    },
    "run_qlib_unified_backtest": {
        "description": "使用Qlib执行统一回测框架",
        "domain": "backtest",
        "tags": ["backtest", "qlib", "unified"],
    },
    "get_cn_financial_statements": {
        "description": "获取A股公司财务报表数据（利润表/资产负债表/现金流量表）",
        "domain": "financial",
        "tags": ["financial", "statement", "fundamental"],
    },
    "get_cn_research_reports": {
        "description": "获取券商研究报告摘要和评级",
        "domain": "financial",
        "tags": ["research", "report", "rating"],
    },
    "get_tdx_financial_data": {
        "description": "获取通达信财务数据",
        "domain": "financial",
        "tags": ["tdx", "financial"],
    },
    "get_cn_longhu_for_symbol": {
        "description": "获取A股龙虎榜数据，查看主力资金动向",
        "domain": "financial",
        "tags": ["longhu", "institutional", "fund_flow"],
    },
    "get_stock_news": {
        "description": "获取股票相关新闻资讯",
        "domain": "news",
        "tags": ["news", "sentiment", "information"],
    },
    "get_news_sentiment": {
        "description": "分析新闻情感倾向，生成看多/看空信号",
        "domain": "news",
        "tags": ["sentiment", "nlp", "signal"],
    },
    "get_market_mood": {
        "description": "获取市场整体情绪指标（恐慌/贪婪指数）",
        "domain": "news",
        "tags": ["mood", "sentiment", "fear_greed"],
    },
    "stock_selector": {
        "description": "智能选股，支持多条件筛选和技术面/基本面过滤",
        "domain": "selection",
        "tags": ["screening", "selection", "filter"],
    },
    "get_user_watchlist": {
        "description": "获取用户自选股列表",
        "domain": "selection",
        "tags": ["watchlist", "portfolio", "user"],
    },
    "get_research_pipeline_status": {
        "description": "查看研究Pipeline执行状态",
        "domain": "research",
        "tags": ["pipeline", "status", "research"],
    },
    "run_intelligent_pipeline": {
        "description": "执行智能研究Pipeline，自动化数据分析流程",
        "domain": "research",
        "tags": ["pipeline", "automation", "research"],
    },
    "search_web_intelligence": {
        "description": "搜索互联网金融情报信息",
        "domain": "news",
        "tags": ["web", "search", "intelligence"],
    },
    "get_yanbao_market_digest": {
        "description": "获取研报市场摘要，汇总当日重要研报观点",
        "domain": "news",
        "tags": ["yanbao", "digest", "summary"],
    },
}


def register_existing_tools(
    tool_bindings: list[Any],
    *,
    registry: CapabilityRegistry | None = None,
) -> int:
    """Register LangChain @tool bindings as capabilities with semantic metadata.

    Returns the number of tools registered.
    """
    reg = registry or get_capability_registry()
    registered = 0
    for tool_fn in tool_bindings:
        tool_name = getattr(tool_fn, "name", None) or getattr(tool_fn, "__name__", None)
        if not tool_name:
            continue
        meta = _TOOL_SEMANTICS.get(tool_name, {})
        cap = reg.get(tool_name)
        if cap is not None:
            continue
        from app.core.capability_registry import Capability

        cap = Capability(
            name=tool_name,
            description=meta.get("description", getattr(tool_fn, "description", "")),
            domain=meta.get("domain", ""),
            tags=tuple(meta.get("tags", [])),
            input_schema=getattr(tool_fn, "args_schema", None) or {},
            handler=tool_fn,
        )
        reg.register(cap)
        registered += 1
    if registered:
        logger.info("CapabilityRegistry: registered %d tools from QuantToolBindings", registered)
    return registered


def get_agent_capabilities(
    *,
    domains: list[str] | None = None,
    registry: CapabilityRegistry | None = None,
) -> list[dict[str, Any]]:
    """Return capabilities formatted for AI agent consumption (OpenAI function-calling)."""
    reg = registry or get_capability_registry()
    return reg.to_agent_tools(domains=domains)


def search_capabilities(query: str, *, limit: int = 5) -> list[dict[str, Any]]:
    """Semantic search for capabilities. Returns list of {name, description, domain}."""
    reg = get_capability_registry()
    results = reg.search(query, limit=limit)
    return [
        {"name": c.name, "description": c.description, "domain": c.domain, "tags": list(c.tags)}
        for c in results
    ]
