"""Attach decision provenance summary to any API response."""

from __future__ import annotations

from functools import wraps
from typing import Any

from flask import jsonify

from app.modules.system.services.ui.decision_provenance_service import (
    DecisionProvenanceService,
)
from app.domain.dto.decision_context_dto import DecisionContextDTO


def _build_provenance_summary(dto: DecisionContextDTO) -> dict[str, Any]:
    return {
        "decision_id": dto.decision_id,
        "subject": dto.subject,
        "model_version": dto.model_version,
        "created_at": dto.created_at,
        "evidence_count": len(dto.evidence),
        "reasoning_trace": dto.reasoning_trace,
    }


def with_provenance(subject_factory, model_version: str = "unknown"):
    """Decorator: appends a `provenance` key to the JSON response.

    Args:
        subject_factory: callable returning the decision subject (symbol/task name).
        model_version: model version tag attached to the trace.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            response = func(*args, **kwargs)
            payload = response.get_json() if hasattr(response, "get_json") else None
            if not isinstance(payload, dict):
                return response
            subject = (
                subject_factory(*args, **kwargs)
                if callable(subject_factory)
                else str(subject_factory or "")
            )
            if not subject:
                return response
            svc = DecisionProvenanceService()
            evidence = payload.get("evidence") if isinstance(payload.get("evidence"), list) else None
            dto = svc.build_context(
                subject=subject,
                model_version=model_version,
                input_snapshot=payload.get("input_snapshot"),
                reasoning_trace=payload.get("reasoning_trace"),
                evidence=evidence,
            )
            payload["provenance"] = _build_provenance_summary(dto)
            return jsonify(payload)
        return wrapper
    return decorator
