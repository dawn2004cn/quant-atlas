from __future__ import annotations

from typing import Any

from flask import Response

from app.domain.self_healing_base import SelfHealingErrorMixin


class SelfHealingDomainError(SelfHealingErrorMixin, Exception):
    CODE = "SELF_HEALING_DOMAIN_ERROR"
    STATUS_CODE = 400

    def __init__(
        self,
        message: str,
        *,
        code: str = "DOMAIN_ERROR",
        details: dict[str, Any] | None = None,
        hints: list[dict[str, str]] | None = None,
        degraded_tag: str | None = None,
    ) -> None:
        super().__init__(message, code, details)
        self.hints = list(hints or [])
        self.degraded_tag = degraded_tag


def apply_degraded_headers(response: Response, error: BaseException) -> Response:
    if isinstance(error, SelfHealingErrorMixin) and error.degraded_tag:
        response.headers["X-QC-Degraded"] = str(error.degraded_tag)
    hints = getattr(error, "hints", None)
    if hints:
        import json
        response.headers["X-QC-Hints"] = json.dumps(hints, ensure_ascii=False)
    return response
