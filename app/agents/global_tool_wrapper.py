from __future__ import annotations
"""Global Tool Wrapper - Knowledge Intermediary IO Optimization.

This module implements from midify_plan13.md:
- GlobalToolWrapper: Wraps all quant_tools to use evidence-aware caching
- Single entry point for tool configuration
- Eliminates redundant API calls by checking blackboard first

Usage:
    wrapper = create_global_tool_wrapper()
    wrapped_tools = wrapper.wrap_all_tools(quant_tools)
"""

from datetime import datetime
from typing import Any
from collections.abc import Callable

from .evidence_blackboard import (
    get_evidence_blackboard,
    EvidenceBlackboard,
    EvidenceType,
    EvidenceStrength,
)
from .knowledge_intermediary import EvidenceAwareCache

from app.core.logger import get_logger

logger = get_logger(__name__)


class GlobalToolWrapper:
    """Global tool wrapper that applies evidence-aware caching to all tools.

    Logic:
    1. Check if tool data already exists in blackboard
    2. If yes, return from blackboard (no API call)
    3. If no, call tool and write result to blackboard
    4. Other agents can now read from blackboard without API calls
    """

    def __init__(self, blackboard: EvidenceBlackboard | None = None):
        self._blackboard = blackboard or get_evidence_blackboard()
        self._cache = EvidenceAwareCache()
        self._wrapped_tools: dict[str, Callable] = {}

    def wrap_tool(
        self,
        tool_func: Callable,
        tool_name: str,
        evidence_key: str,
        evidence_type: EvidenceType = EvidenceType.QUANTITATIVE,
    ) -> Callable:
        """Wrap a single tool with evidence-aware caching."""
        async def wrapped_tool(*args, **kwargs) -> Any:
            ticker = kwargs.get("symbol") or kwargs.get("ticker") or (args[0] if args else "")

            if not ticker:
                return await tool_func(*args, **kwargs)

            existing = await self._blackboard.read_evidence(ticker, evidence_key)
            if existing:
                logger.info(f"Tool {tool_name}: using cached evidence for {ticker}/{evidence_key}")
                return {
                    "from_blackboard": True,
                    "data": existing,
                    "cached_at": datetime.now().isoformat(),
                }

            result = await tool_func(*args, **kwargs)

            if result and not isinstance(result, dict) or (isinstance(result, dict) and result.get("success") is not False):
                evidence_value = result.get("data", result) if isinstance(result, dict) else result
                await self._blackboard.write_evidence(
                    ticker,
                    evidence_key,
                    evidence_value,
                    evidence_type,
                    EvidenceStrength.MEDIUM,
                    tool_name,
                )

                await self._cache.cache_result(tool_name, kwargs, result)

            return result

        wrapped_tool.__name__ = tool_name
        wrapped_tool._is_wrapped = True
        wrapped_tool._original_tool = tool_func

        self._wrapped_tools[tool_name] = wrapped_tool
        return wrapped_tool

    def wrap_all_tools(
        self,
        tools: list[Any],
    ) -> list[Any]:
        """Wrap all tools with evidence-aware caching."""
        wrapped = []

        tool_key_map = {
            "get_market_data": ("market_data", EvidenceType.PRICE),
            "get_kline_chart": ("kline_data", EvidenceType.PRICE),
            "get_cn_financial_statements": ("financial_statements", EvidenceType.FUNDAMENTAL),
            "get_stock_news": ("stock_news", EvidenceType.SENTIMENT),
            "run_backtest": ("backtest_result", EvidenceType.ANALYSIS),
            "get_qlib_factor_snapshot": ("qlib_factors", EvidenceType.QUANTITATIVE),
            "get_cn_longhu_for_symbol": ("longhu_data", EvidenceType.SENTIMENT),
            "stock_selector": ("stock_selector", EvidenceType.OTHER),
            "probe_ticker": ("ticker_probe", EvidenceType.OTHER),
        }

        for tool in tools:
            tool_name = getattr(tool, "name", str(tool))

            evidence_key, evidence_type = tool_key_map.get(
                tool_name,
                (tool_name.lower(), EvidenceType.OTHER),
            )

            wrapped_tool = self.wrap_tool(tool, tool_name, evidence_key, evidence_type)
            wrapped.append(wrapped_tool)

        logger.info(f"Wrapped {len(wrapped)} tools with evidence-aware caching")
        return wrapped

    def get_blackboard_stats(self) -> dict[str, Any]:
        """Get blackboard statistics."""
        return {
            "wrapped_tools_count": len(self._wrapped_tools),
            "tool_names": list(self._wrapped_tools.keys()),
        }


_global_wrapper: GlobalToolWrapper | None = None


def get_global_tool_wrapper() -> GlobalToolWrapper:
    """Get singleton global tool wrapper."""
    global _global_wrapper
    if _global_wrapper is None:
        _global_wrapper = GlobalToolWrapper()
    return _global_wrapper


def create_global_tool_wrapper() -> GlobalToolWrapper:
    """Factory to create global tool wrapper."""
    return GlobalToolWrapper()


def wrap_quant_tools(tools: list[Any]) -> list[Any]:
    """Convenience function to wrap all quant tools."""
    wrapper = get_global_tool_wrapper()
    return wrapper.wrap_all_tools(tools)
