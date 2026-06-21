"""Domain port: Repository contract for user LLM config persistence."""

from __future__ import annotations

from typing import Any, Protocol


class UserLlmConfigRepositoryPort(Protocol):
    """Data access interface for user-level LLM configurations."""

    def get_by_user_provider(self, user_id: int, provider: str) -> dict[str, Any] | None:
        """Get decrypted config for a user+provider. Returns None if not found."""
        ...

    def list_by_user(self, user_id: int) -> list[dict[str, Any]]:
        """List all configs for a user (safe, no encrypted keys)."""
        ...

    def get_system_default(self, provider: str) -> dict[str, Any] | None:
        """Get system-wide default config (user_id=0)."""
        ...

    def upsert(self, user_id: int, provider: str, config: dict[str, Any]) -> None:
        """Insert or update a user config. Caller must encrypt api_key first."""
        ...

    def delete(self, user_id: int, provider: str) -> None:
        """Soft-delete: set is_active=0."""
        ...
