from __future__ import annotations

"""LLM ReAct 工具循环（LangChain / LangGraph 节点内使用）。"""


import json
from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import BaseTool

from ...core.logger import get_logger

logger = get_logger(__name__)


def tool_result_payload(result: Any) -> str:
    if hasattr(result, "model_dump_json"):
        return result.model_dump_json()
    try:
        return json.dumps(result, default=str, ensure_ascii=False)
    except TypeError:
        return str(result)


async def react_with_tools(
    llm: BaseChatModel,
    tools: list[BaseTool],
    *,
    system: str,
    user: str,
    max_rounds: int = 8,
) -> str:
    """ReAct：LLM ↔ ToolMessage，直到无 tool_calls 或达到轮数上限。"""
    if not tools:
        ai = await llm.ainvoke([SystemMessage(content=system), HumanMessage(content=user)])
        return str(ai.content) if isinstance(ai, AIMessage) else ""

    bound = llm.bind_tools(tools)
    messages: list[BaseMessage] = [SystemMessage(content=system), HumanMessage(content=user)]
    name_to_tool = {t.name: t for t in tools}

    for _ in range(max_rounds):
        ai = await bound.ainvoke(messages)
        messages.append(ai)
        if not isinstance(ai, AIMessage) or not ai.tool_calls:
            return str(ai.content or "")

        for call in ai.tool_calls:
            name = call.get("name") or ""
            tid = call.get("id") or ""
            raw_args = call.get("args") or {}
            tool = name_to_tool.get(name)
            if tool is None:
                payload = json.dumps({"ok": False, "error": f"unknown_tool:{name}"}, ensure_ascii=False)
            else:
                try:
                    out = await tool.ainvoke(raw_args) if hasattr(tool, "ainvoke") else tool.invoke(raw_args)
                    payload = tool_result_payload(out)
                except Exception as exc:
                    logger.warning("tool %s failed: %s", name, exc)
                    payload = json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False)
            messages.append(ToolMessage(content=payload, tool_call_id=tid, name=name))

    tail = messages[-1]
    return str(tail.content) if isinstance(tail, AIMessage) else ""
