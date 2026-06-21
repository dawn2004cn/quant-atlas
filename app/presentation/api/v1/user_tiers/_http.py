"""Shared HTTP helpers for user tier routes."""

from __future__ import annotations

from typing import Any

from flask import jsonify

from app.presentation.api.error_codes import ErrorCode, error_payload
from app.presentation.api.responses import success_response


def tier_success(data: Any = None, *, meta: dict[str, Any] | None = None):
    return success_response(data=data, meta=meta)


def tier_not_found(message: str):
    payload = error_payload(ErrorCode.NOT_FOUND, message)
    return jsonify(payload), ErrorCode.NOT_FOUND.http_status
