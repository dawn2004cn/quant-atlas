"""API v1: Identity resolution endpoint for dual-track auth (JWT + cookie)."""

from __future__ import annotations

from flask import Blueprint, g, jsonify

from app.core.registry import register_routes


@register_routes(name="auth_identity", context="system", description="Identity resolution for dual-track auth")
def register_auth_identity_routes(blueprint: Blueprint, ctx=None) -> None:

    @blueprint.get("/auth/whoami")
    def whoami():
        """Return current identity.
        ---
        get:
          tags: [auth]
          summary: Get current authenticated identity
          responses:
            200:
              description: Current identity
              content:
                application/json:
                  schema:
                    type: object
                    properties:
                      user_id:
                        type: string
                      auth_source:
                        type: string
                        enum: [jwt, jwt_cookie, cookie]
            401:
              description: Unauthorized
        """
        if not g.get("identity_subject"):
            return jsonify({"error": "unauthorized"}), 401
        return jsonify({
            "user_id": g.identity_subject,
            "auth_source": g.identity_source,
        })

    whoami._apispec_path = True