"""Key management service — secure CRUD for encrypted API credentials."""

from __future__ import annotations

from datetime import datetime

from app.core.key_encryption import KeyEncryptionService
from app.core.logger import get_logger

logger = get_logger(__name__)


class KeyManagementService:
    """Securely store, retrieve, and rotate API keys."""

    def __init__(self, session=None, encryption_key: str | None = None):
        self._session = session
        self._kms = KeyEncryptionService(secret_key=encryption_key)

    def _get_session(self):
        return self._session

    def set_gateway_key(self, gateway_name: str, api_key: str) -> int:
        """Encrypt and store an API key for a gateway.

        Returns the gateway config record ID.
        """
        from app.infrastructure.database.models import GatewayConfig

        session = self._get_session()
        if session is None:
            raise RuntimeError("KeyManagementService requires a SQLAlchemy session")

        encrypted = self._kms.encrypt(api_key)
        record = session.query(GatewayConfig).filter_by(gateway_name=gateway_name).first()
        if record is None:
            record = GatewayConfig(
                gateway_name=gateway_name,
                api_key_encrypted=encrypted,
            )
            session.add(record)
        else:
            record.api_key_encrypted = encrypted
            record.updated_at = datetime.utcnow()
        session.flush()
        logger.info("Key stored for gateway %s", gateway_name)
        return record.id

    def get_gateway_key(self, gateway_name: str) -> str:
        """Retrieve the plaintext API key for a gateway."""
        from app.infrastructure.database.models import GatewayConfig

        session = self._get_session()
        if session is None:
            raise RuntimeError("KeyManagementService requires a SQLAlchemy session")

        record = session.query(GatewayConfig).filter_by(gateway_name=gateway_name).first()
        if record is None or not record.api_key_encrypted:
            raise KeyError(f"Gateway {gateway_name} not found")
        return self._kms.decrypt(record.api_key_encrypted)

    def list_gateways(self) -> list[dict]:
        """List gateways without exposing keys."""
        from app.infrastructure.database.models import GatewayConfig

        session = self._get_session()
        if session is None:
            raise RuntimeError("KeyManagementService requires a SQLAlchemy session")

        records = session.query(GatewayConfig).all()
        return [
            {
                "id": r.id,
                "gateway_name": r.gateway_name,
                "is_active": bool(r.is_active),
                "priority": r.priority,
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "updated_at": r.updated_at.isoformat() if r.updated_at else None,
            }
            for r in records
        ]

    def set_openbb_key(self, provider_name: str, api_key: str) -> None:
        """Encrypt and store an API key for an OpenBB provider."""
        from app.infrastructure.database.models import OpenBBProviderConfig

        session = self._get_session()
        if session is None:
            raise RuntimeError("KeyManagementService requires a SQLAlchemy session")

        encrypted = self._kms.encrypt(api_key)
        record = session.query(OpenBBProviderConfig).filter_by(provider_name=provider_name).first()
        if record is None:
            record = OpenBBProviderConfig(
                provider_name=provider_name,
                api_key_encrypted=encrypted,
            )
            session.add(record)
        else:
            record.api_key_encrypted = encrypted
            record.updated_at = datetime.utcnow()

    def get_openbb_key(self, provider_name: str) -> str:
        """Retrieve the plaintext API key for an OpenBB provider."""
        from app.infrastructure.database.models import OpenBBProviderConfig

        session = self._get_session()
        if session is None:
            raise RuntimeError("KeyManagementService requires a SQLAlchemy session")

        record = session.query(OpenBBProviderConfig).filter_by(provider_name=provider_name).first()
        if record is None or not record.api_key_encrypted:
            raise KeyError(f"OpenBB provider {provider_name} not found")
        return self._kms.decrypt(record.api_key_encrypted)
