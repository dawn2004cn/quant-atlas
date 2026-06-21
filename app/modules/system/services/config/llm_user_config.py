from __future__ import annotations
"""前端可选的 LLM 提供方：列举模型与构建 LangChain Chat 模型。"""


import logging
from typing import Any

import requests
from langchain_core.language_models.chat_models import BaseChatModel

from app.application.errors import ValidationError


from app.core.logger import get_logger

logger = get_logger(__name__)

# OpenAI 兼容 /v1/models
_OPENAI_COMPAT_IDS = frozenset(
    {"ollama", "openai", "openrouter", "dashscope", "xai", "groq", "deepseek"},
)

_DEFAULT_BASE_V1: dict[str, str] = {
    "ollama": "http://127.0.0.1:11434/v1",
    "openai": "https://api.openai.com/v1",
    "openrouter": "https://openrouter.ai/api/v1",
    "dashscope": "https://dashscope.aliyuncs.com/compatible-mode/v1",
    "xai": "https://api.x.ai/v1",
    "groq": "https://api.groq.com/openai/v1",
    "deepseek": "https://api.deepseek.com/v1",
}


def list_public_providers() -> list[dict[str, Any]]:
    """供 GET /api/v1/llm/providers 使用（无密钥）。"""
    return [
        {
            "id": "dashscope",
            "name": "阿里百炼（DashScope 兼容模式）",
            "kind": "openai_compat",
            "default_base_url": _DEFAULT_BASE_V1["dashscope"],
            "needs_api_key": True,
        },
        {
            "id": "openai",
            "name": "OpenAI",
            "kind": "openai_compat",
            "default_base_url": _DEFAULT_BASE_V1["openai"],
            "needs_api_key": True,
        },
        {
            "id": "gemini",
            "name": "Google Gemini",
            "kind": "google_genai",
            "default_base_url": "",
            "needs_api_key": True,
        },
        {
            "id": "xai",
            "name": "xAI（Grok）",
            "kind": "openai_compat",
            "default_base_url": _DEFAULT_BASE_V1["xai"],
            "needs_api_key": True,
        },
        {
            "id": "openrouter",
            "name": "OpenRouter",
            "kind": "openai_compat",
            "default_base_url": _DEFAULT_BASE_V1["openrouter"],
            "needs_api_key": True,
        },
        {
            "id": "groq",
            "name": "Groq",
            "kind": "openai_compat",
            "default_base_url": _DEFAULT_BASE_V1["groq"],
            "needs_api_key": True,
        },
        {
            "id": "deepseek",
            "name": "DeepSeek",
            "kind": "openai_compat",
            "default_base_url": _DEFAULT_BASE_V1["deepseek"],
            "needs_api_key": True,
        },
        {
            "id": "ollama",
            "name": "Ollama（本机）",
            "kind": "openai_compat",
            "default_base_url": _DEFAULT_BASE_V1["ollama"],
            "needs_api_key": False,
        },
    ]


def _normalize_openai_v1_base(url: str) -> str:
    u = url.strip().rstrip("/")
    if u.endswith("/v1"):
        return u
    return f"{u}/v1"


def _resolve_openai_compat_base(provider_id: str, user_base: str | None) -> str:
    if user_base and str(user_base).strip():
        return _normalize_openai_v1_base(str(user_base))
    d = _DEFAULT_BASE_V1.get(provider_id)
    if not d:
        raise ValidationError(f"未知提供方: {provider_id}")
    return d


def fetch_openai_compatible_model_ids(base_v1: str, api_key: str, *, max_models: int = 500) -> list[str]:
    url = f"{base_v1.rstrip('/')}/models"
    headers = {"Authorization": f"Bearer {api_key}"}
    try:
        resp = requests.get(url, headers=headers, timeout=28)
        resp.raise_for_status()
    except requests.RequestException as exc:
        logger.warning("list models failed: %s", exc)
        raise ValidationError(f"无法拉取模型列表（请检查 Base URL 与 API Key）: {exc}") from exc
    try:
        data = resp.json()
    except ValueError as exc:
        raise ValidationError("模型列表响应不是合法 JSON") from exc
    rows = data.get("data") if isinstance(data, dict) else None
    if not isinstance(rows, list):
        raise ValidationError("模型列表格式异常（缺少 data 数组）")
    ids: list[str] = []
    for row in rows:
        if isinstance(row, dict):
            mid = row.get("id")
            if isinstance(mid, str) and mid.strip():
                ids.append(mid.strip())
    out = sorted(set(ids))
    if len(out) > max_models:
        out = out[:max_models]
    return out


def fetch_gemini_model_ids(api_key: str, *, max_models: int = 200) -> list[str]:
    key = (api_key or "").strip()
    if not key:
        raise ValidationError("Gemini 需要 API Key")
    url = "https://generativelanguage.googleapis.com/v1beta/models"
    try:
        resp = requests.get(url, params={"key": key}, timeout=28)
        resp.raise_for_status()
    except requests.RequestException as exc:
        logger.warning("gemini list models failed: %s", exc)
        raise ValidationError(f"无法拉取 Gemini 模型列表: {exc}") from exc
    try:
        data = resp.json()
    except ValueError as exc:
        raise ValidationError("Gemini 模型列表响应不是合法 JSON") from exc
    models = data.get("models") if isinstance(data, dict) else None
    if not isinstance(models, list):
        raise ValidationError("Gemini 模型列表格式异常")
    out: list[str] = []
    for m in models:
        if not isinstance(m, dict):
            continue
        name = m.get("name", "")
        methods = m.get("supportedGenerationMethods") or []
        if "generateContent" not in methods:
            continue
        if not isinstance(name, str) or not name.startswith("models/"):
            continue
        short = name.replace("models/", "", 1)
        if short:
            out.append(short)
    out = sorted(set(out))
    if len(out) > max_models:
        out = out[:max_models]
    return out


def fetch_models_for_user(
    provider_id: str,
    api_key: str,
    *,
    base_url: str | None = None,
) -> list[str]:
    pid = (provider_id or "").strip().lower()
    if pid in ("x", "xai"):
        pid = "xai"
    if pid == "gemini":
        return fetch_gemini_model_ids(api_key)
    if pid not in _OPENAI_COMPAT_IDS:
        raise ValidationError(f"不支持的提供方: {provider_id}")
    base = _resolve_openai_compat_base(pid, base_url)
    key = (api_key or "").strip()
    if not key:
        if pid == "ollama":
            key = "ollama"
        else:
            raise ValidationError("需要填写 API Key 才能刷新模型列表")
    return fetch_openai_compatible_model_ids(base, key)


def _chat_openai_user(
    *,
    base_v1: str,
    api_key: str,
    model: str,
    temperature: float,
    timeout_sec: int,
) -> BaseChatModel:
    from langchain_openai import ChatOpenAI

    return ChatOpenAI(
        model=model,
        base_url=base_v1.rstrip("/"),
        api_key=api_key,
        temperature=temperature,
        timeout=timeout_sec,
    )


def build_langchain_llm_from_profile(profile: dict[str, Any]) -> BaseChatModel:
    """
    根据前端提交的 ``llm`` 对象构建 Chat 模型。

    profile 键：provider, api_key, model, base_url（可选）, temperature（可选）, timeout_sec（可选）
    """
    if not isinstance(profile, dict):
        raise ValidationError("llm 配置格式错误")
    provider_id = str(profile.get("provider") or "").strip().lower()
    if provider_id in ("x", "xai"):
        provider_id = "xai"
    model = str(profile.get("model") or "").strip()
    if not provider_id:
        raise ValidationError("llm.provider 不能为空")
    if not model:
        raise ValidationError("llm.model 不能为空")

    temperature = float(profile.get("temperature", 0.2))
    timeout_sec = int(profile.get("timeout_sec", 120))
    api_key = str(profile.get("api_key") or "").strip()
    base_url = profile.get("base_url")
    base_opt = str(base_url).strip() if base_url else None

    if provider_id == "gemini":
        if not api_key:
            raise ValidationError("Gemini 需要 api_key")
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
        except ImportError as exc:  # pragma: no cover
            raise ValidationError(
                "使用 Gemini 需安装依赖：pip install langchain-google-genai google-generativeai"
            ) from exc
        client = ChatGoogleGenerativeAI(
            model=model,
            google_api_key=api_key,
            temperature=temperature,
            timeout=timeout_sec,
        )
        from app.core.metrics_helpers import instrument_chat_model

        return instrument_chat_model(client, model_name=model, call_type="chat")

    if provider_id not in _OPENAI_COMPAT_IDS:
        raise ValidationError(f"不支持的提供方: {provider_id}")

    base_v1 = _resolve_openai_compat_base(provider_id, base_opt)
    if not api_key:
        if provider_id == "ollama":
            api_key = "ollama"
        else:
            raise ValidationError("llm.api_key 不能为空")

    client = _chat_openai_user(
        base_v1=base_v1,
        api_key=api_key,
        model=model,
        temperature=temperature,
        timeout_sec=timeout_sec,
    )
    from app.core.metrics_helpers import instrument_chat_model

    return instrument_chat_model(client, model_name=model, call_type="chat")

