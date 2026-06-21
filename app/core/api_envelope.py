"""Unified API response envelope.

All route handlers should use ApiEnvelope.ok() / ApiEnvelope.error() to
return a consistent {ok, data, meta} shape.  This eliminates the P07
dual-response-format tech debt.
"""

from __future__ import annotations

from typing import Any


class ApiEnvelope:
    """Single, universally-adopted response envelope for all API routes."""

    @staticmethod
    def ok(data: Any, meta: dict[str, Any] | None = None) -> dict[str, Any]:
        return {"ok": True, "data": data, "meta": meta or {}}

    @staticmethod
    def error(
        code: str,
        message: str,
        details: Any = None,
        status: int = 400,
    ) -> dict[str, Any]:
        return {
            "ok": False,
            "data": None,
            "meta": {
                "error": {
                    "code": code,
                    "message": message,
                    "details": details,
                    "status": status,
                }
            },
        }
