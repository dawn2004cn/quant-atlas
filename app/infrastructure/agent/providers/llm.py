"""LLM factory and JSON extraction helpers.

Ported from Vibe-Trading.
统一使用 app.core.llm_config.LLMFactory 作为配置来源。
"""

from __future__ import annotations

import os
from typing import Any

from app.core.llm_config import LLMFactory
from app.modules.system.services.config.llm_user_config import build_langchain_llm_from_profile

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None  # type: ignore

try:
    from langchain_openai import ChatOpenAI
except ImportError:
    ChatOpenAI = None  # type: ignore

try:
    from langchain_ollama import ChatOllama
except ImportError:
    ChatOllama = None  # type: ignore


if ChatOpenAI is not None:
    class ChatOpenAIWithReasoning(ChatOpenAI):
        """ChatOpenAI that preserves provider reasoning across invoke + stream."""

        @staticmethod
        def _capture(src: Any, msg: Any) -> None:
            if value := src.get("reasoning_content") or src.get("reasoning"):
                msg.additional_kwargs["reasoning_content"] = value

        def _create_chat_result(self, response, generation_info=None):
            result = super()._create_chat_result(response, generation_info)
            raw = response if isinstance(response, dict) else response.model_dump()
            for gen, choice in zip(result.generations, raw["choices"], strict=False):
                self._capture(choice["message"], gen.message)
            return result

        def _convert_chunk_to_generation_chunk(
            self,
            chunk: dict,
            default_chunk_class: type,
            base_generation_info: dict | None,
        ):
            gen = super()._convert_chunk_to_generation_chunk(
                chunk, default_chunk_class, base_generation_info
            )
            if gen is None:
                return None
            choices = chunk.get("choices") or chunk.get("chunk", {}).get("choices")
            if choices:
                self._capture(choices[0]["delta"], gen.message)
            return gen

        def _get_request_payload(
            self,
            input_: Any,
            *,
            stop: list[str] | None = None,
            **kwargs: Any,
        ) -> dict:
            payload = super()._get_request_payload(input_, stop=stop, **kwargs)
            messages = super()._convert_input(input_).to_messages()
            for i, m in enumerate(payload["messages"]):
                if m.get("role") != "assistant":
                    continue
                if m.get("content") is None:
                    m["content"] = ""
                m["reasoning_content"] = messages[i].additional_kwargs.get("reasoning_content", "")
            return payload
else:
    ChatOpenAIWithReasoning = None


def _ensure_dotenv() -> None:
    if load_dotenv is not None:
        load_dotenv(override=False)


def _sync_provider_env() -> None:
    _ensure_dotenv()
    provider = os.getenv("LANGCHAIN_PROVIDER", "openai").lower()

    _PROVIDER_MAP: dict[str, tuple[str | None, str]] = {
        "openai":     ("OPENAI_API_KEY",     "OPENAI_BASE_URL"),
        "openrouter": ("OPENROUTER_API_KEY",  "OPENROUTER_BASE_URL"),
        "deepseek":   ("DEEPSEEK_API_KEY",    "DEEPSEEK_BASE_URL"),
        "gemini":     ("GEMINI_API_KEY",      "GEMINI_BASE_URL"),
        "groq":       ("GROQ_API_KEY",        "GROQ_BASE_URL"),
        "dashscope":  ("DASHSCOPE_API_KEY",   "DASHSCOPE_BASE_URL"),
        "qwen":       ("DASHSCOPE_API_KEY",   "DASHSCOPE_BASE_URL"),
        "zhipu":      ("ZHIPU_API_KEY",       "ZHIPU_BASE_URL"),
        "moonshot":   ("MOONSHOT_API_KEY",    "MOONSHOT_BASE_URL"),
        "minimax":    ("MINIMAX_API_KEY",     "MINIMAX_BASE_URL"),
        "ollama":     (None,                  "OLLAMA_BASE_URL"),
    }

    spec = _PROVIDER_MAP.get(provider, _PROVIDER_MAP["openai"])
    key_env, base_env = spec

    if key_env is not None:
        api_key = os.getenv(key_env, "") or os.getenv("OPENAI_API_KEY", "")
    else:
        api_key = os.getenv("OPENAI_API_KEY", "") or "ollama"

    base_url = os.getenv(base_env, "") or os.getenv("OPENAI_BASE_URL", "") or os.getenv("OPENAI_API_BASE", "")

    if api_key:
        os.environ["OPENAI_API_KEY"] = api_key
    if base_url:
        os.environ["OPENAI_API_BASE"] = base_url
        os.environ.setdefault("OPENAI_BASE_URL", base_url)


def build_llm(*, model_name: str | None = None, callbacks: Any = None) -> Any:
    """构建 LLM 实例 - 统一使用 LLMFactory 配置

    Args:
        model_name: 可选的模型覆盖（会覆盖 LLM_MODEL 配置）
        callbacks: 可选的回调函数
    """
    config = LLMFactory.get_config()
    name = model_name or config.model
    temperature = float(os.getenv("LANGCHAIN_TEMPERATURE", str(config.temperature)))
    if not name:
        raise RuntimeError("LLM_MODEL is not set - configure in .env")
    profile = {
        "provider": config.provider,
        "api_key": config.api_key if config.api_key != "EMPTY" else "",
        "model": name,
        "base_url": config.base_url,
        "temperature": temperature,
        "timeout_sec": int(config.timeout),
    }
    client = build_langchain_llm_from_profile(profile)
    if callbacks and hasattr(client, "callbacks"):
        client.callbacks = callbacks
    return client
