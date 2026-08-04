from __future__ import annotations

from enum import Enum


class ErrorCode(str, Enum):
    """Canonical error codes for the Quant-Atlas API.

    Each code maps to a machine-readable identifier used in API responses,
    error catalogs, and i18n message lookups.
    """

    # ── Validation ─────────────────────────────────────────
    VALIDATION_ERROR = "validation_error"
    SYMBOL_REQUIRED = "symbol_required"
    MARKET_REQUIRED = "market_required"
    SYMBOL_AND_PEER_REQUIRED = "symbol_and_peer_required"
    INVALID_MIN_LEVEL = "invalid_min_level"

    # ── Authentication / Authorization ─────────────────────
    UNAUTHORIZED = "unauthorized"
    FORBIDDEN = "forbidden"
    INVALID_SESSION = "invalid_session"

    # ── Resource ───────────────────────────────────────────
    NOT_FOUND = "not_found"
    ENTITY_NOT_FOUND = "entity_not_found"
    CONTEXT_UNAVAILABLE = "context_unavailable"

    # ── Service ────────────────────────────────────────────
    SERVICE_ERROR = "service_error"
    SERVICE_UNAVAILABLE = "service_unavailable"
    EXTERNAL_SERVICE_ERROR = "external_service_error"
    MARKET_SERVICE_UNAVAILABLE = "market_service_unavailable"

    # ── Data ───────────────────────────────────────────────
    DATA_STALE = "data_stale"
    MYSQL_NOT_ENABLED = "mysql_not_enabled"
    TIMESCALEDB_NOT_ENABLED = "timescaledb_not_enabled"

    # ── Internal ───────────────────────────────────────────
    INTERNAL_ERROR = "internal_error"
    UNPROCESSABLE = "unprocessable"

    # ── Infrastructure ─────────────────────────────────────
    STRATEGY_NOT_CONFIGURED = "strategy_service not configured, enable Qlib or check ENABLE_QLIB"

    @property
    def http_status(self) -> int:
        mapping = {
            ErrorCode.UNAUTHORIZED: 401,
            ErrorCode.FORBIDDEN: 403,
            ErrorCode.NOT_FOUND: 404,
            ErrorCode.ENTITY_NOT_FOUND: 404,
            ErrorCode.UNPROCESSABLE: 422,
            ErrorCode.VALIDATION_ERROR: 400,
            ErrorCode.INTERNAL_ERROR: 500,
            ErrorCode.EXTERNAL_SERVICE_ERROR: 503,
            ErrorCode.SERVICE_UNAVAILABLE: 503,
        }
        return mapping.get(self, 400)


def error_payload(code: ErrorCode, message: str, details: dict | None = None) -> dict:
    return {
        "status": "error",
        "error": {
            "code": code.value,
            "message": message,
            "details": details or {},
        },
    }
