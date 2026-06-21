"""Core service: LLMProviderService with hierarchical config resolution.

Priority chain:
    User config (user_llm_configs) -> System default (user_id=0) -> Provider default (hardcoded)
"""

from __future__ import annotations

import json
from dataclasses import replace
from typing import Any

from app.core.key_encryption import KeyEncryptionService
from app.core.logger import get_logger
from app.domain.ports.llm_config_repo_port import UserLlmConfigRepositoryPort
from app.domain.ports.llm_port import LlmProviderPort, ResolvedLlmConfig
from app.modules.system.services.config.llm_user_config import (
    build_langchain_llm_from_profile,
)

logger = get_logger(__name__)


# System-wide default provider config (code-level fallback)
_PROVIDER_DEFAULTS: dict[str, dict[str, Any]] = {
    "openai": {
        "model_name": "gpt-4o-mini",
        "base_url": "https://api.openai.com/v1",
        "temperature": 0.2,
        "max_tokens": 4096,
        "timeout_sec": 120,
    },
    "deepseek": {
        "model_name": "deepseek-chat",
        "base_url": "https://api.deepseek.com/v1",
        "temperature": 0.2,
        "max_tokens": 4096,
        "timeout_sec": 120,
    },
    "ollama": {
        "model_name": "qwen2.5:7b",
        "base_url": "http://127.0.0.1:11434/v1",
        "temperature": 0.2,
        "max_tokens": 4096,
        "timeout_sec": 300,
    },
    "gemini": {
        "model_name": "gemini-2.0-flash",
        "base_url": None,
        "temperature": 0.2,
        "max_tokens": 4096,
        "timeout_sec": 120,
    },
    "groq": {
        "model_name": "llama-3.3-70b",
        "base_url": "https://api.groq.com/openai/v1",
        "temperature": 0.2,
        "max_tokens": 4096,
        "timeout_sec": 60,
    },
    "openrouter": {
        "model_name": "google/gemma-2-9b",
        "base_url": "https://openrouter.ai/api/v1",
        "temperature": 0.2,
        "max_tokens": 4096,
        "timeout_sec": 120,
    },
    "xai": {
        "model_name": "grok-2",
        "base_url": "https://api.x.ai/v1",
        "temperature": 0.2,
        "max_tokens": 4096,
        "timeout_sec": 120,
    },
    "dashscope": {
        "model_name": "qwen-plus",
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "temperature": 0.2,
        "max_tokens": 4096,
        "timeout_sec": 120,
    },
}

# Logical model alias mappings → physical models per provider
_MODEL_ALIASES: dict[str, dict[str, str]] = {
    "high_precision": {
        "openai": "gpt-4o",
        "deepseek": "deepseek-chat",
        "ollama": "qwen2.5:32b",
        "gemini": "gemini-2.0-pro",
        "groq": "llama-3.3-70b",
        "openrouter": "openai/gpt-4o",
        "xai": "grok-2",
        "dashscope": "qwen-max",
    },
    "fast_reasoning": {
        "openai": "gpt-4o-mini",
        "deepseek": "deepseek-chat",
        "ollama": "qwen2.5:7b",
        "gemini": "gemini-2.0-flash",
        "groq": "llama-3.1-8b",
        "openrouter": "google/gemma-2-9b",
        "xai": "grok-2-mini",
        "dashscope": "qwen-plus",
    },
    "cheap_summary": {
        "openai": "gpt-4o-mini",
        "deepseek": "deepseek-chat",
        "ollama": "qwen2.5:7b",
        "gemini": "gemini-2.0-flash-lite",
        "groq": "llama-3.1-8b",
        "openrouter": "google/gemma-2-9b",
        "xai": "grok-2-mini",
        "dashscope": "qwen-turbo",
    },
}

_DEFAULT_FALLBACK_CHAIN = ["deepseek", "openai", "ollama"]


class LlmProviderService(LlmProviderPort):
    """Hierarchical LLM config resolver + client builder.

    Usage:
        svc = LlmProviderService(repo=repository, key_encryption=kms)
        config = svc.resolve(user_id=42, provider="openai")
        client = svc.build_client(config)
    """

    def __init__(
        self,
        repo: UserLlmConfigRepositoryPort,
        key_encryption: KeyEncryptionService | None = None,
    ):
        self._repo = repo
        self._kms = key_encryption or KeyEncryptionService()

    # ---- Public API ----

    def resolve(self, user_id: int, provider: str = "default") -> ResolvedLlmConfig:
        """Resolve final config: User → SystemDefault → ProviderDefault."""
        # 1. User-specific config
        user_cfg = self._repo.get_by_user_provider(user_id, provider)
        if user_cfg is not None:
            logger.debug("Resolved LLM config for user=%d provider=%s (user-specific)", user_id, provider)
            return ResolvedLlmConfig(**user_cfg)

        # 2. System-wide default (user_id=0)
        default_cfg = self._repo.get_system_default(provider)
        if default_cfg is not None:
            logger.debug("Resolved LLM config for user=%d provider=%s (system default)", user_id, provider)
            return ResolvedLlmConfig(**default_cfg)

        # 3. Provider default (hardcoded)
        defaults = _PROVIDER_DEFAULTS.get(provider, {
            "model_name": "gpt-4o-mini",
            "base_url": None,
            "temperature": 0.2,
            "max_tokens": 4096,
            "timeout_sec": 120,
        })
        config_dict = {
            "provider": provider,
            "model_name": defaults["model_name"],
            "base_url": defaults.get("base_url"),
            "api_key": "",  # empty — will fail at build time if key required
            "temperature": defaults.get("temperature", 0.2),
            "max_tokens": defaults.get("max_tokens", 4096),
            "timeout_sec": defaults.get("timeout_sec", 120),
            "fallback_chain": list(_DEFAULT_FALLBACK_CHAIN),
        }
        logger.debug("Resolved LLM config for user=%d provider=%s (provider default)", user_id, provider)
        return ResolvedLlmConfig(**config_dict)

    def resolve_logical(self, user_id: int, logical_model: str) -> ResolvedLlmConfig:
        """Resolve config for a logical model name (alias → physical)."""
        cfg = self.resolve(user_id, "default")
        alias = (logical_model or "").strip().lower()
        if not alias:
            return cfg
        provider = (cfg.provider or "default").strip().lower()
        physical_model = _MODEL_ALIASES.get(alias, {}).get(provider)
        if physical_model:
            logger.debug("Alias resolved: %s → %s for user=%d", alias, physical_model, user_id)
            return replace(cfg, model_name=physical_model, logical_model=alias)
        if cfg.model_alias and cfg.model_alias.lower() == alias:
            return replace(cfg, logical_model=alias)
        return cfg

    def build_client(self, config: ResolvedLlmConfig) -> Any:
        """Build a langchain BaseChatModel from resolved config."""
        profile = {
            "provider": config.provider,
            "api_key": config.api_key,
            "model": config.model_name,
            "base_url": config.base_url,
            "temperature": config.temperature,
            "timeout_sec": config.timeout_sec,
        }
        return build_langchain_llm_from_profile(profile)

    def save_user_config(
        self,
        user_id: int,
        provider: str,
        model_name: str,
        base_url: str | None,
        api_key: str,
        temperature: float,
        max_tokens: int,
        timeout_sec: int = 120,
        model_alias: str | None = None,
        fallback_chain: list[str] | None = None,
    ) -> None:
        """Encrypt and persist user config."""
        try:
            encrypted_key = self._kms.encrypt(api_key) if api_key else ""
        except Exception as exc:
            logger.error("Failed to encrypt api_key for user=%d: %s", user_id, exc)
            raise

        config_dict = {
            "model_name": model_name,
            "base_url": base_url,
            "api_key_encrypted": encrypted_key,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "timeout_sec": timeout_sec,
            "model_alias": model_alias,
            "fallback_chain_json": json.dumps(fallback_chain, ensure_ascii=False) if fallback_chain else None,
        }
        self._repo.upsert(user_id, provider, config_dict)

    def get_user_configs(self, user_id: int) -> list[dict[str, Any]]:
        """List configs without exposing keys."""
        return self._repo.list_by_user(user_id)

    def get_user_config_detail(self, user_id: int, provider: str) -> dict[str, Any] | None:
        """Get full config detail (decrypted) by provider."""
        return self._repo.get_by_user_provider(user_id, provider)

    def delete_user_config(self, user_id: int, provider: str) -> None:
        """Soft-delete user config."""
        self._repo.delete(user_id, provider)
