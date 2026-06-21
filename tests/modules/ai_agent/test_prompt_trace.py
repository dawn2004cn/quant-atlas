"""Tests for prompt trace attachment."""

from __future__ import annotations

from app.modules.ai_agent.services.prompt_trace import attach_prompt_trace, prompt_hash


def test_prompt_hash_stable():
    assert prompt_hash("hello") == prompt_hash("hello")
    assert prompt_hash("hello") != prompt_hash("world")


def test_attach_prompt_trace_fields():
    out = attach_prompt_trace(
        {"text": "ok"},
        prompt_id="test_prompt",
        prompt_text="analyze this",
        base_version="v1",
    )
    assert out["prompt_id"] == "test_prompt"
    assert out["prompt_version"] == "v1"
    assert out["prompt_hash"] == prompt_hash("analyze this")
    assert out["text"] == "ok"
