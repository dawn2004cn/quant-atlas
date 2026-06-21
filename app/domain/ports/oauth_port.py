"""OAuth provider port — optional external identity (Keycloak / OIDC)."""

from __future__ import annotations

from typing import Any, Protocol


class OAuthProviderPort(Protocol):
    """Exchange authorization codes and introspect access tokens."""

    def is_configured(self) -> bool:
        """Return True when provider env credentials are present."""

    def authorization_url(self, redirect_uri: str, state: str) -> str:
        """Build provider login URL for browser redirect."""

    def exchange_code(self, code: str, redirect_uri: str) -> dict[str, Any]:
        """Trade authorization code for token payload."""

    def introspect(self, access_token: str) -> dict[str, Any]:
        """Validate token and return claims (sub, email, ...)."""
