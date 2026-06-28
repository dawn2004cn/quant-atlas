"""Keycloak OIDC adapter (optional — enabled only when env vars are set)."""

from __future__ import annotations

from typing import Any

from app.core.logger import get_logger
from app.core.runtime_config import get_runtime
from app.domain.exceptions import ValidationError

logger = get_logger(__name__)


class KeycloakOAuthProvider:
    """Thin wrapper around python-keycloak when installed and configured."""

    def __init__(self) -> None:
        self._server_url = get_runtime("KEYCLOAK_SERVER_URL", "").rstrip("/")
        self._realm = get_runtime("KEYCLOAK_REALM", "")
        self._client_id = get_runtime("KEYCLOAK_CLIENT_ID", "")
        self._client_secret = get_runtime("KEYCLOAK_CLIENT_SECRET", "")
        self._client = None
        if self.is_configured():
            try:
                from keycloak import KeycloakOpenID

                self._client = KeycloakOpenID(
                    server_url=self._server_url + "/",
                    client_id=self._client_id,
                    realm_name=self._realm,
                    client_secret_key=self._client_secret,
                )
            except ImportError:
                logger.warning("python-keycloak not installed; OAuth disabled")
            except Exception as exc:
                logger.warning("Keycloak client init failed: %s", exc, exc_info=True)

    def is_configured(self) -> bool:
        return bool(self._server_url and self._realm and self._client_id and self._client_secret)

    def authorization_url(self, redirect_uri: str, state: str) -> str:
        if not self.is_configured() or self._client is None:
            raise ValidationError("OAuth provider not configured")
        return self._client.auth_url(redirect_uri=redirect_uri, scope="openid profile email", state=state)

    def exchange_code(self, code: str, redirect_uri: str) -> dict[str, Any]:
        if not self.is_configured() or self._client is None:
            raise ValidationError("OAuth provider not configured")
        return self._client.token(grant_type="authorization_code", code=code, redirect_uri=redirect_uri)

    def introspect(self, access_token: str) -> dict[str, Any]:
        if not self.is_configured() or self._client is None:
            raise ValidationError("OAuth provider not configured")
        return self._client.introspect(access_token)


class NullOAuthProvider:
    """No-op provider used when OAuth is not configured."""

    def is_configured(self) -> bool:
        return False

    def authorization_url(self, redirect_uri: str, state: str) -> str:
        raise ValidationError("OAuth provider not configured")

    def exchange_code(self, code: str, redirect_uri: str) -> dict[str, Any]:
        raise ValidationError("OAuth provider not configured")

    def introspect(self, access_token: str) -> dict[str, Any]:
        raise ValidationError("OAuth provider not configured")


def build_oauth_provider() -> KeycloakOAuthProvider | NullOAuthProvider:
    provider = KeycloakOAuthProvider()
    return provider if provider.is_configured() else NullOAuthProvider()


def extract_subject_from_token_response(
    provider: KeycloakOAuthProvider | NullOAuthProvider,
    token_payload: dict[str, Any],
) -> tuple[str, str | None]:
    """Resolve OAuth subject and display label from a token exchange payload."""
    access = str(token_payload.get("access_token") or "").strip()
    if not access:
        return "", None
    try:
        claims = provider.introspect(access)
    except Exception as exc:
        logger.warning("OAuth token introspect failed: %s", exc, exc_info=True)
        return "", None
    if not isinstance(claims, dict):
        return "", None
    sub = str(claims.get("sub") or "").strip()
    if not sub:
        return "", None
    label = (
        claims.get("email")
        or claims.get("preferred_username")
        or claims.get("name")
    )
    display = str(label).strip() if label else None
    return sub, display
