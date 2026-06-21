"""Domain port: LLM provider service interface and resolved config value object."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass(frozen=True, slots=True)
class ResolvedLlmConfig:
    """Result of hierarchical config resolution.

    Priority: UserConfig → SystemDefault → ProviderDefault (env/hardcoded).
    """

    provider: str
    model_name: str
    base_url: str | None
    api_key: str
    temperature: float
    max_tokens: int
    timeout_sec: int
    model_alias: str | None = None
    logical_model: str | None = None
    fallback_chain: list[str] = field(default_factory=lambda: ["deepseek", "openai", "ollama"])


class LlmProviderPort(Protocol):
    """Contract for per-user LLM configuration resolution."""

    def resolve(self, user_id: int, provider: str = "default") -> ResolvedLlmConfig:
        """Resolve final config for a user + provider hint."""
        ...

    def resolve_logical(self, user_id: int, logical_model: str) -> ResolvedLlmConfig:
        """Resolve config via a logical model name (alias)."""
        ...

    def build_client(self, config: ResolvedLlmConfig) -> Any:
        """Build a langchain BaseChatModel from resolved config."""
        ...

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
        """Save (upsert) a user-specific LLM config."""
        ...

    def get_user_configs(self, user_id: int) -> list[dict[str, Any]]:
        """List all configs for a user (without exposing encrypted keys)."""
        ...

    def get_user_config_detail(
        self, user_id: int, provider: str
    ) -> dict[str, Any] | None:
        """Get full user config detail by provider."""
        ...

    def delete_user_config(self, user_id: int, provider: str) -> None:
        """Delete a user-specific LLM config (logical delete)."""
        ...
