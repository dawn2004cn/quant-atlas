"""Flask hooks for P3 strategic feature sunset."""

from __future__ import annotations

from functools import wraps
from typing import Any, TypeVar
from collections.abc import Callable

from flask import Flask, Blueprint, jsonify, render_template, request

from app.core.strategic_sunset import (
    api_path_sunset_feature,
    feature_enabled,
    feature_env_key,
    feature_label,
    jinja_feature_flags,
)

F = TypeVar("F", bound=Callable[..., Any])

_RETIRED_MESSAGE = (
    "该能力已在 P3 战略削减中默认下线（审计建议）。"
    "如需在开发环境启用，请设置对应 FEATURE_*=1。"
)


def retired_api_response(feature: str) -> tuple[Any, int]:
    return (
        jsonify(
            {
                "ok": False,
                "status": "error",
                "error": {
                    "code": "feature_retired",
                    "message": _RETIRED_MESSAGE,
                    "details": {
                        "feature": feature,
                        "label": feature_label(feature),
                    },
                },
            }
        ),
        410,
    )


def register_strategic_sunset(app: Flask) -> None:
    """Jinja globals + optional API guard (also attach via blueprint)."""

    @app.context_processor
    def _inject_sunset_flags() -> dict[str, bool]:
        return jinja_feature_flags()


def attach_api_sunset_guard(blueprint: Blueprint) -> None:
    @blueprint.before_request
    def _block_retired_api() -> Any | None:
        feature = api_path_sunset_feature(request.path)
        if feature and not feature_enabled(feature):
            return retired_api_response(feature)
        return None


def require_strategic_feature(feature: str) -> Callable[[F], F]:
    """Page route guard — returns 410 + retired template when disabled."""

    def decorator(view: F) -> F:
        @wraps(view)
        def wrapped(*args: Any, **kwargs: Any) -> Any:
            if not feature_enabled(feature):
                return (
                    render_template(
                        "feature_retired.html",
                        feature=feature,
                        feature_label=feature_label(feature),
                        env_hint=f"{feature_env_key(feature)}=1",
                    ),
                    410,
                )
            return view(*args, **kwargs)

        return wrapped  # type: ignore[return-value]

    return decorator
