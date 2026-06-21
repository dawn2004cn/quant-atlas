from __future__ import annotations

from typing import Any

import pytest

from app.application.services.llm_provider_service import LlmProviderService
from app.domain.ports.llm_port import ResolvedLlmConfig


class FakeRepo:
    def __init__(self, rows: dict[tuple[int, str], dict[str, Any]] | None = None):
        self.rows = rows or {}

    def get_by_user_provider(self, user_id: int, provider: str) -> dict[str, Any] | None:
        return self.rows.get((user_id, provider))

    def get_system_default(self, provider: str) -> dict[str, Any] | None:
        return self.rows.get((0, provider))

    def upsert(self, user_id: int, provider: str, config: dict[str, Any]) -> None:
        self.rows[(user_id, provider)] = config

    def list_by_user(self, user_id: int) -> list[dict[str, Any]]:
        return [row for (uid, _), row in self.rows.items() if uid == user_id]

    def delete(self, user_id: int, provider: str) -> None:
        self.rows.pop((user_id, provider), None)


def row(provider: str, model_name: str, base_url: str = "http://example.test/v1") -> dict[str, Any]:
    return {
        "provider": provider,
        "model_name": model_name,
        "base_url": base_url,
        "api_key": "test-key",
        "temperature": 0.2,
        "max_tokens": 4096,
        "timeout_sec": 120,
        "model_alias": None,
        "fallback_chain": [provider],
    }


def test_default_provider_resolves_user_default_before_system_default():
    repo = FakeRepo({
        (7, "default"): row("deepseek", "user-default-model"),
        (0, "default"): row("openai", "system-default-model"),
    })
    service = LlmProviderService(repo)

    config = service.resolve(7, "default")

    assert config.provider == "deepseek"
    assert config.model_name == "user-default-model"


def test_logical_alias_maps_default_provider_to_physical_model():
    repo = FakeRepo({
        (7, "default"): row("openai", "old-model"),
    })
    service = LlmProviderService(repo)

    config = service.resolve_logical(7, "high_precision")

    assert config.provider == "openai"
    assert config.logical_model == "high_precision"
    assert config.model_name == "gpt-4o"


def test_legacy_build_llm_uses_unified_profile_builder(monkeypatch):
    from app.core.llm_config import LLMConfig
    from app.infrastructure.agent.providers import llm as legacy_llm

    captured = {}

    def fake_config():
        return LLMConfig(
            provider="openai",
            model="gpt-4o-mini",
            api_key="secret",
            base_url="http://proxy.test/v1",
            timeout=45,
            is_local=False,
            temperature=0.4,
        )

    def fake_builder(profile):
        captured.update(profile)
        return object()

    monkeypatch.setattr(legacy_llm.LLMFactory, "get_config", fake_config)
    monkeypatch.setattr(legacy_llm, "build_langchain_llm_from_profile", fake_builder)

    legacy_llm.build_llm(model_name="override-model")

    assert captured == {
        "provider": "openai",
        "api_key": "secret",
        "model": "override-model",
        "base_url": "http://proxy.test/v1",
        "temperature": 0.4,
        "timeout_sec": 45,
    }


class FakeProviderForFallback:
    def __init__(self, failures: dict[str, Exception]):
        self.failures = failures
        self.calls = []

    def resolve(self, user_id: int, provider: str = "default") -> ResolvedLlmConfig:
        return ResolvedLlmConfig(
            provider=provider,
            model_name=f"{provider}-model",
            base_url="http://example.test/v1",
            api_key="key",
            temperature=0.2,
            max_tokens=4096,
            timeout_sec=120,
        )

    def build_client(self, config: ResolvedLlmConfig):
        return config.provider


@pytest.mark.asyncio
async def test_fallback_router_switches_to_next_provider_on_connection_error(monkeypatch):
    from app.application.services.llm_fallback_service import LlmFallbackRouter
    provider = FakeProviderForFallback({"deepseek": ConnectionError("down")})
    router = LlmFallbackRouter(provider, default_chain=["deepseek", "openai"])

    async def fake_call(client, messages, config, provider_name):
        provider.calls.append(provider_name)
        if provider_name in provider.failures:
            raise provider.failures[provider_name]
        return type("Response", (), {"content": "ok", "model": config.model_name, "usage": {}})()

    monkeypatch.setattr(router, "_call_single_provider", fake_call)

    response = await router.call_with_fallback(user_id=7, messages=[])

    assert response.content == "ok"
    assert provider.calls == ["deepseek", "openai"]


@pytest.mark.asyncio
async def test_fallback_router_does_not_switch_on_4xx(monkeypatch):
    from app.application.services.llm_fallback_service import LlmFallbackRouter

    class BadRequest(Exception):
        response = type("R", (), {"status_code": 401})()

    provider = FakeProviderForFallback({"deepseek": BadRequest("bad key")})
    router = LlmFallbackRouter(provider, default_chain=["deepseek", "openai"])

    async def fake_call(client, messages, config, provider_name):
        provider.calls.append(provider_name)
        raise provider.failures[provider_name]

    monkeypatch.setattr(router, "_call_single_provider", fake_call)

    with pytest.raises(BadRequest):
        await router.call_with_fallback(user_id=7, messages=[])

    assert provider.calls == ["deepseek"]


async def test_fallback_router_does_not_switch_on_4xx(monkeypatch):
    from app.application.services.llm_fallback_service import LlmFallbackRouter

    class BadRequest(Exception):
        response = type("R", (), {"status_code": 401})()

    provider = FakeProviderForFallback({"deepseek": BadRequest("bad key")})
    router = LlmFallbackRouter(provider, default_chain=["deepseek", "openai"])

    async def fake_call(client, messages, config, provider_name):
        provider.calls.append(provider_name)
        raise provider.failures[provider_name]

    monkeypatch.setattr(router, "_call_single_provider", fake_call)

    with pytest.raises(BadRequest):
        await router.call_with_fallback(user_id=7, messages=[])

    assert provider.calls == ["deepseek"]


def test_build_client_uses_resolved_config_profile(monkeypatch):
    captured = {}

    def fake_builder(profile):
        captured.update(profile)
        return object()

    monkeypatch.setattr(
        "app.application.services.llm_provider_service.build_langchain_llm_from_profile",
        fake_builder,
    )
    service = LlmProviderService(FakeRepo())
    config = ResolvedLlmConfig(
        provider="openai",
        model_name="gpt-4o-mini",
        base_url="http://proxy.test/v1",
        api_key="secret",
        temperature=0.3,
        max_tokens=2048,
        timeout_sec=30,
    )

    service.build_client(config)

    assert captured == {
        "provider": "openai",
        "api_key": "secret",
        "model": "gpt-4o-mini",
        "base_url": "http://proxy.test/v1",
        "temperature": 0.3,
        "timeout_sec": 30,
    }
