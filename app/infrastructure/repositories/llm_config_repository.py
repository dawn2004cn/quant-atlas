"""Repository: SQLAlchemy implementation of UserLlmConfigRepositoryPort."""

from __future__ import annotations

import json
from typing import Any

from app.core.key_encryption import KeyEncryptionService
from app.core.logger import get_logger
from app.domain.ports.llm_config_repo_port import UserLlmConfigRepositoryPort

logger = get_logger(__name__)


class SqlAlchemyUserLlmConfigRepository(UserLlmConfigRepositoryPort):
    """Persists and retrieves user LLM configs with Fernet encryption."""

    def __init__(self, session: Any, key_encryption: KeyEncryptionService | None = None):
        self._session = session
        self._kms = key_encryption or KeyEncryptionService()

    def _get_session(self) -> Any:
        return self._session

    def get_by_user_provider(self, user_id: int, provider: str) -> dict[str, Any] | None:
        """Get decrypted config for user+provider."""
        session = self._get_session()
        from app.infrastructure.database.models import UserLlmConfig

        record = (
            session.query(UserLlmConfig)
            .filter_by(user_id=user_id, provider=provider, is_active=1)
            .first()
        )
        if record is None:
            return None
        return self._to_dict_decrypted(record)

    def list_by_user(self, user_id: int) -> list[dict[str, Any]]:
        """List all configs for a user (safe, no encrypted keys)."""
        session = self._get_session()
        from app.infrastructure.database.models import UserLlmConfig

        records = (
            session.query(UserLlmConfig)
            .filter_by(user_id=user_id, is_active=1)
            .order_by(UserLlmConfig.updated_at.desc())
            .all()
        )
        return [
            {
                "id": r.id,
                "provider": r.provider,
                "model_name": r.model_name,
                "base_url": r.base_url,
                "temperature": r.temperature,
                "max_tokens": r.max_tokens,
                "timeout_sec": r.timeout_sec,
                "model_alias": r.model_alias,
                "fallback_chain": self._parse_fallback_chain(r.fallback_chain_json),
                "is_active": bool(r.is_active),
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "updated_at": r.updated_at.isoformat() if r.updated_at else None,
            }
            for r in records
        ]

    def get_system_default(self, provider: str) -> dict[str, Any] | None:
        """Get system-wide default config (user_id=0)."""
        return self.get_by_user_provider(user_id=0, provider=provider)

    def upsert(self, user_id: int, provider: str, config: dict[str, Any]) -> None:
        """Insert or update. Caller must encrypt api_key first."""
        from app.infrastructure.database.models import UserLlmConfig

        session = self._get_session()
        record = (
            session.query(UserLlmConfig)
            .filter_by(user_id=user_id, provider=provider)
            .first()
        )
        if record is None:
            record = UserLlmConfig(user_id=user_id, provider=provider)
            session.add(record)
        # Update fields
        for field_name in ("model_name", "base_url", "api_key_encrypted", "temperature",
                           "max_tokens", "timeout_sec", "model_alias", "fallback_chain_json"):
            if field_name in config:
                setattr(record, field_name, config[field_name])
        record.is_active = 1
        record.updated_at = __import__("datetime").datetime.now()
        session.flush()
        logger.info("Upserted user_llm_config for user=%d provider=%s", user_id, provider)

    def delete(self, user_id: int, provider: str) -> None:
        """Soft-delete: set is_active=0."""
        from app.infrastructure.database.models import UserLlmConfig

        session = self._get_session()
        record = (
            session.query(UserLlmConfig)
            .filter_by(user_id=user_id, provider=provider, is_active=1)
            .first()
        )
        if record is not None:
            record.is_active = 0
            record.updated_at = __import__("datetime").datetime.now()
            session.flush()
            logger.info("Deleted user_llm_config for user=%d provider=%s", user_id, provider)

    # ---- helpers ----

    def _to_dict_decrypted(self, record: Any) -> dict[str, Any]:
        """Convert ORM record to dict with decrypted api_key."""
        try:
            api_key_plain = self._kms.decrypt(record.api_key_encrypted)
        except Exception as exc:  # pragma: no cover
            logger.error("Failed to decrypt api_key for user=%d provider=%s: %s",
                         record.user_id, record.provider, exc)
            api_key_plain = "*** decryption failed ***"
        return {
            "provider": record.provider,
            "model_name": record.model_name,
            "base_url": record.base_url,
            "api_key": api_key_plain,
            "temperature": record.temperature,
            "max_tokens": record.max_tokens,
            "timeout_sec": record.timeout_sec,
            "model_alias": record.model_alias,
            "fallback_chain": self._parse_fallback_chain(record.fallback_chain_json),
        }

    @staticmethod
    def _parse_fallback_chain(json_str: str | None) -> list[str]:
        if not json_str:
            return ["deepseek", "openai", "ollama"]
        try:
            items = json.loads(json_str)
            if isinstance(items, list):
                return [str(p).strip() for p in items if str(p).strip()]
        except (ValueError, TypeError):
            logger.warning("Suppressed exception", exc_info=True)
            pass
        return ["deepseek", "openai", "ollama"]
