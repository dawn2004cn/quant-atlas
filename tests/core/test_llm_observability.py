"""Tests for Phase 7.4 LLM observability — token/latency extraction."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch


# ── _extract_usage ─────────────────────────────────────────────────────────


def _import_module():
    """Import the adapter module (avoid importing the full agents chain)."""
    import importlib
    import sys

    # Block the problematic import chain
    sys.modules["app.agents"] = MagicMock()
    sys.modules["app.agents.research"] = MagicMock()
    sys.modules["app.agents.research.react_loop"] = MagicMock()

    from app.infrastructure.adapters import llm_universal_adapter as mod
    return mod


def test_extract_usage_from_usage_metadata() -> None:
    """LangChain ≥0.2.x AIMessage.usage_metadata."""
    mod = _import_module()

    mock_response = MagicMock()
    mock_response.usage_metadata = {
        "input_tokens": 100,
        "output_tokens": 50,
        "total_tokens": 150,
    }
    mock_response.content = "test"

    usage = mod._extract_usage(mock_response)
    assert usage["prompt_tokens"] == 100
    assert usage["completion_tokens"] == 50
    assert usage["total_tokens"] == 150


def test_extract_usage_from_response_metadata() -> None:
    """Older LangChain: token usage in response_metadata."""
    mod = _import_module()

    mock_response = MagicMock()
    mock_response.usage_metadata = None
    mock_response.response_metadata = {
        "token_usage": {
            "prompt_tokens": 80,
            "completion_tokens": 40,
            "total_tokens": 120,
        }
    }
    mock_response.content = "test"

    usage = mod._extract_usage(mock_response)
    assert usage["prompt_tokens"] == 80
    assert usage["completion_tokens"] == 40


def test_extract_usage_from_direct_usage() -> None:
    """Custom usage attribute."""
    mod = _import_module()

    mock_response = MagicMock()
    mock_response.usage_metadata = None
    mock_response.response_metadata = None
    mock_response.usage = {"input_tokens": 30, "output_tokens": 10, "total": 40}
    mock_response.content = "test"

    usage = mod._extract_usage(mock_response)
    assert usage == {"input_tokens": 30, "output_tokens": 10, "total": 40}


def test_extract_usage_none_response() -> None:
    mod = _import_module()
    assert mod._extract_usage(None) == {}


def test_normalize_usage_casts_to_int() -> None:
    mod = _import_module()

    raw = {"prompt_tokens": "100", "completion_tokens": 50.5, "total_tokens": None}
    norm = mod._normalize_usage(raw)
    assert norm == {"prompt_tokens": 100, "completion_tokens": 50}
    assert "total_tokens" not in norm  # None is dropped


def test_normalize_usage_invalid_values() -> None:
    mod = _import_module()

    raw = {"prompt_tokens": "not_a_number", "completion_tokens": 20}
    norm = mod._normalize_usage(raw)
    assert norm == {"completion_tokens": 20}


# ── _ObservabilityCallbacks ────────────────────────────────────────────────


def test_callbacks_capture_usage() -> None:
    mod = _import_module()

    cb = mod._ObservabilityCallbacks()
    cb.before_call("openai", "gpt-4o")

    mock_resp = MagicMock()
    mock_resp.usage_metadata = {"input_tokens": 50, "output_tokens": 25, "total_tokens": 75}
    mock_resp.content = "hello"
    cb.after_call(mock_resp)

    assert cb.success is True
    assert cb.usage["prompt_tokens"] == 50
    assert cb.usage["completion_tokens"] == 25
    assert cb.usage["total_tokens"] == 75


def test_callbacks_empty_on_no_response() -> None:
    mod = _import_module()

    cb = mod._ObservabilityCallbacks()
    cb.before_call("ollama", "qwen2.5")
    # No after_call — should return empty
    assert cb.usage == {}
    assert cb.success is False


# ── UniversalLlmAdapter._call_direct ───────────────────────────────────────


def test_call_direct_extract_usage() -> None:
    mod = _import_module()

    mock_client = AsyncMock()
    mock_response = MagicMock()
    mock_response.content = "analysis complete"
    mock_response.usage_metadata = {
        "input_tokens": 200,
        "output_tokens": 100,
        "total_tokens": 300,
    }
    mock_client.ainvoke = AsyncMock(return_value=mock_response)

    mock_config = MagicMock()
    mock_config.provider = "openai"
    mock_config.model_name = "gpt-4o"

    import asyncio

    adapter = mod.UniversalLlmAdapter(
        provider_service=MagicMock(),
        fallback_router=None,
    )
    result = asyncio.get_event_loop().run_until_complete(
        adapter._call_direct(mock_client, [], mock_config),
    )

    assert result.content == "analysis complete"
    assert result.model == "gpt-4o"
    assert result.usage["prompt_tokens"] == 200
    assert result.usage["completion_tokens"] == 100
    assert result.usage["total_tokens"] == 300


def test_call_direct_no_usage_metadata() -> None:
    mod = _import_module()

    mock_client = AsyncMock()
    mock_response = MagicMock()
    mock_response.content = "bare response"
    mock_response.usage_metadata = None
    mock_response.response_metadata = None
    mock_client.ainvoke = AsyncMock(return_value=mock_response)

    mock_config = MagicMock()
    mock_config.model_name = "unknown-model"

    import asyncio

    adapter = mod.UniversalLlmAdapter(
        provider_service=MagicMock(),
        fallback_router=None,
    )
    result = asyncio.get_event_loop().run_until_complete(
        adapter._call_direct(mock_client, [], mock_config),
    )

    assert result.content == "bare response"
    assert result.model == "unknown-model"
    assert result.usage == {}


def test_call_direct_error_returns_usage() -> None:
    mod = _import_module()

    mock_client = AsyncMock()
    mock_client.ainvoke = AsyncMock(side_effect=RuntimeError("model not found"))

    mock_config = MagicMock()
    mock_config.model_name = "broken-model"

    import asyncio

    adapter = mod.UniversalLlmAdapter(
        provider_service=MagicMock(),
        fallback_router=None,
    )
    result = asyncio.get_event_loop().run_until_complete(
        adapter._call_direct(mock_client, [], mock_config),
    )

    assert result.content == ""
    assert result.model == "broken-model"
    assert "error" in result.usage


# ── FallbackRouter._call_single_provider ───────────────────────────────────


def test_fallback_router_extract_usage() -> None:
    from app.application.services.llm_fallback_service import (
        LlmFallbackRouter,
        _extract_usage,
        _normalize_usage,
    )

    mock_response = MagicMock()
    mock_response.content = "fallback answer"
    mock_response.usage_metadata = {
        "input_tokens": 60,
        "output_tokens": 30,
        "total_tokens": 90,
    }

    usage = _normalize_usage(_extract_usage(mock_response))
    assert usage["prompt_tokens"] == 60
    assert usage["completion_tokens"] == 30
    assert usage["total_tokens"] == 90


def test_fallback_router_empty_usage() -> None:
    from app.application.services.llm_fallback_service import _extract_usage

    mock_response = MagicMock()
    mock_response.usage_metadata = None
    mock_response.response_metadata = None

    assert _extract_usage(mock_response) == {}
