from __future__ import annotations
from app.domain.dto.service_result import GenericResponseDTO
"""TradingAgents 聊天专用：通过 CapabilityRegistry 动态发现工具。"""


from typing import Any

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

from app.agents.research.react_loop import react_with_tools
from app.core.capability_bridge import get_agent_capabilities
from core.llm_config import get_llm_for_user
from app.core.logger import get_logger


logger = get_logger(__name__)

CHAT_SYSTEM_PROMPT = """你是一个专业的量化投资助手，可以访问股票市场数据。

## 可用工具
你可以根据用户需求动态选择以下工具：
- get_market_data: 获取市场行情（大势判断）
- probe_ticker: 查询个股信息（代码、名称、现价、涨跌幅）
- get_kline_chart: 获取K线数据用于技术分析
- get_user_watchlist: 查看用户自选股
- get_stock_news: 获取个股新闻（多空情绪）
- get_cn_financial_statements: 读取财务报表（基本面）
- stock_selector: 筛选符合条件的股票
- 以及其他注册到能力注册表的工具

## 回复要求
1. 如果用户问的是具体股票，先用工具查询数据
2. 用数据说话，客观分析
3. 简洁明了，不绕弯子
4. 用户未指定市场时，默认 A 股
5. 如果不确定就说不知道，不要编造数据"""


async def _resolve_tools() -> list[Any]:
    """Resolve available tools from CapabilityRegistry (dynamic discovery).

    Falls back to a hardcoded default list if the registry is empty
    (e.g. during bootstrap before tools are registered).
    """
    try:
        caps = get_agent_capabilities()
        if caps:
            logger.debug("Dynamic tool discovery: %d capabilities found", len(caps))
            # get_agent_capabilities returns dicts; react_with_tools expects
            # callable tool functions. We resolve the handler from the registry.
            from app.core.capability_registry import get_capability_registry

            reg = get_capability_registry()
            resolved = []
            for cap_info in caps:
                handler = reg.get(cap_info["name"])
                if handler and handler.handler:
                    resolved.append(handler.handler)
                else:
                    # Keep the name for logging but skip if no handler
                    logger.debug("Capability %s has no handler — skipping", cap_info["name"])
            if resolved:
                return resolved
    except Exception as exc:
        logger.warning("Dynamic tool discovery failed — %s, falling back to defaults", exc)

    # Fallback: hardcoded default tools
    logger.info("Using fallback hardcoded tool list")
    from app.tools.quant_tools import (
        get_market_data,
        get_kline_chart,
        stock_selector,
        probe_ticker,
        get_user_watchlist,
        get_stock_news,
        get_cn_financial_statements,
    )
    return [
        get_market_data,
        probe_ticker,
        get_kline_chart,
        get_user_watchlist,
        get_stock_news,
        get_cn_financial_statements,
        stock_selector,
    ]


async def run_chat_with_tools(
    message: str,
    user_id: int,
    conversation_history: list[dict] | None = None,
) -> GenericResponseDTO:
    """Chat with dynamic tool discovery via CapabilityRegistry.

    Unlike the old hardcoded tool list, this resolves available tools
    from the registry at call time, enabling runtime tool registration
    and removal without code changes.
    """
    llm = get_llm_for_user(user_id)

    # Dynamic tool discovery
    tools = await _resolve_tools()
    logger.info("run_chat_with_tools: resolved %d tools for user=%d", len(tools), user_id)

    # Build message history
    messages = [SystemMessage(content=CHAT_SYSTEM_PROMPT)]

    # Add conversation history (last 10 rounds)
    if conversation_history:
        for i, msg in enumerate(conversation_history[-20:]):
            role = msg.get("role", "")
            content = msg.get("content", "")
            if role == "user":
                messages.append(HumanMessage(content=content))
            elif role == "assistant":
                messages.append(AIMessage(content=content))

    # Add current message
    messages.append(HumanMessage(content=message))

    try:
        # ReAct mode
        result = await react_with_tools(
            llm,
            tools,
            system=CHAT_SYSTEM_PROMPT,
            user=message,
            max_rounds=8,
        )
        return {
            "ok": True,
            "summary": result,
            "agent_summary": result,
        }
    except Exception as e:
        return {
            "ok": False,
            "error": str(e),
            "summary": f"抱歉，处理请求时出错: {str(e)}",
            "agent_summary": f"抱歉，处理请求时出错: {str(e)}",
        }


async def run_chat_streaming(
    message: str,
    user_id: int,
    conversation_history: list[dict] | None = None,
):
    """Streaming chat version with dynamic tool discovery."""
    llm = get_llm_for_user(user_id)

    # Dynamic tool discovery
    tools = await _resolve_tools()

    async def on_chunk(chunk: str):
        yield chunk

    messages = [HumanMessage(content=message)]

    try:
        async for chunk in llm.astream(
            messages,
            tools=tools,
            system=CHAT_SYSTEM_PROMPT,
        ):
            yield chunk.content
    except Exception as e:
        yield f"错误: {str(e)}"
