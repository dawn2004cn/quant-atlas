from __future__ import annotations
"""ChatLLM: raw LLM message interface with function calling support.

Ported from Vibe-Trading.
"""


from dataclasses import dataclass, field
from typing import Any

from app.infrastructure.agent.providers.llm import build_llm


def _dedupe_finish_reason(raw: str) -> str:
    return next(
        (m for m in ("tool_calls", "function_call", "content_filter", "length", "stop")
         if raw.endswith(m)),
        raw,
    )


@dataclass
class ToolCallRequest:
    id: str
    name: str
    arguments: dict[str, Any]


@dataclass
class LLMResponse:
    content: str | None = None
    tool_calls: list[ToolCallRequest] = field(default_factory=list)
    reasoning_content: str | None = None
    finish_reason: str = "stop"

    @property
    def has_tool_calls(self) -> bool:
        return len(self.tool_calls) > 0


class ChatLLM:
    """LLM chat client with function calling support."""

    def __init__(self, model_name: str | None = None) -> None:
        self.model_name = model_name
        self._llm = build_llm(model_name=model_name)

    def chat(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]] | None = None, timeout: int | None = None) -> LLMResponse:
        llm = self._llm.bind_tools(tools) if tools else self._llm
        config = {"timeout": timeout} if timeout else {}
        ai_message = llm.invoke(messages, config=config)
        return self._parse_response(ai_message)

    def stream_chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        on_text_chunk: Any | None = None,
        timeout: int | None = None,
    ) -> LLMResponse:
        try:
            llm = self._llm.bind_tools(tools) if tools else self._llm
            config = {"timeout": timeout} if timeout else {}
            accumulated = None
            for chunk in llm.stream(messages, config=config):
                if chunk.content and on_text_chunk:
                    on_text_chunk(chunk.content)
                accumulated = chunk if accumulated is None else accumulated + chunk
            if accumulated is None:
                return LLMResponse(content="", tool_calls=[], finish_reason="stop")
            return self._parse_response(accumulated)
        except Exception:
            return self.chat(messages, tools=tools, timeout=timeout)

    async def achat(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]] | None = None, timeout: int | None = None) -> LLMResponse:
        llm = self._llm.bind_tools(tools) if tools else self._llm
        config = {"timeout": timeout} if timeout else {}
        ai_message = await llm.ainvoke(messages, config=config)
        return self._parse_response(ai_message)

    @staticmethod
    def _parse_response(ai_message: Any) -> LLMResponse:
        return LLMResponse(
            content=ai_message.content,
            tool_calls=[
                ToolCallRequest(id=tc["id"], name=tc["name"], arguments=tc["args"])
                for tc in ai_message.tool_calls
            ],
            reasoning_content=ai_message.additional_kwargs.get("reasoning_content"),
            finish_reason=_dedupe_finish_reason(
                ai_message.response_metadata.get("finish_reason", "stop")
            ),
        )
