"""Tests for @service_fallback / @deps_service_fallback degraded responses."""

from __future__ import annotations

from types import SimpleNamespace

from flask import Flask

from app.presentation.api.decorators import (
    SERVICE_UNAVAILABLE_FALLBACK_DATA,
    deps_service_fallback,
    service_fallback,
)
from app.presentation.api.error_codes import ErrorCode


def test_service_unavailable_fallback_data_uses_error_code():
    assert SERVICE_UNAVAILABLE_FALLBACK_DATA["code"] == ErrorCode.SERVICE_UNAVAILABLE.value
    assert SERVICE_UNAVAILABLE_FALLBACK_DATA["available"] is False


def test_service_fallback_injects_error_code():
    app = Flask(__name__)
    ctx = SimpleNamespace(enable_legacy_response_fields=False, demo_service=None)

    def register(blueprint):
        @blueprint.get("/demo")
        @service_fallback("demo_service")
        def demo():
            return {"ok": True}

    bp = Flask(__name__)
    register(bp)

    @bp.get("/demo-wrapped")
    @service_fallback("demo_service")
    def demo_wrapped():
        _ = ctx
        return {"ok": True}

    with bp.test_request_context("/demo-wrapped"):
        resp = demo_wrapped()
    body = resp[0].get_json()
    assert body["ok"] is True
    assert body["data"]["code"] == ErrorCode.SERVICE_UNAVAILABLE.value


def test_deps_service_fallback_injects_error_code():
    app = Flask(__name__)

    @app.get("/demo-deps")
    @deps_service_fallback(lambda: None, legacy=lambda: False)
    def demo_deps():
        return {"ok": True}

    with app.test_request_context("/demo-deps"):
        resp = demo_deps()
    body = resp[0].get_json()
    assert body["data"]["code"] == ErrorCode.SERVICE_UNAVAILABLE.value


def test_error_code_service_unavailable_http_status():
    assert ErrorCode.SERVICE_UNAVAILABLE.http_status == 503
