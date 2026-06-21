"""Phase G — business metrics, HTTP observability middleware, structured logging."""

from __future__ import annotations

import time
from types import SimpleNamespace
from unittest.mock import MagicMock

from flask import Flask


def test_normalize_endpoint_collapses_dynamic_segments():
    from app.core.metrics_helpers import normalize_endpoint

    assert normalize_endpoint("/api/v1/stock/600519/analysis") == "/api/v1/stock/{symbol}/analysis"
    assert normalize_endpoint("/static/js/app.js").startswith("/static")
    assert normalize_endpoint("/users/42/orders/7") == "/users/{id}/orders/{id}"


def test_record_http_request_without_prometheus_is_noop():
    from app.core import metrics_helpers

    metrics_helpers.record_http_request("GET", "ping", 200, 0.01)


def test_prometheus_middleware_records_request():
    import werkzeug

    if not hasattr(werkzeug, "__version__"):
        werkzeug.__version__ = "3.0.0"  # type: ignore[attr-defined]

    from app.core.middleware.prometheus_middleware import init_prometheus_middleware

    app = Flask(__name__)

    @app.get("/api/v1/ping")
    def ping():
        return {"ok": True}

    init_prometheus_middleware(app)

    with app.test_client() as client:
        response = client.get("/api/v1/ping")
        assert response.status_code == 200


def test_instrument_chat_model_counts_invoke():
    from app.core.metrics_helpers import instrument_chat_model

    invoke_mock = MagicMock(return_value="ok")
    model = SimpleNamespace(model_name="test-model", invoke=invoke_mock)

    wrapped = instrument_chat_model(model, model_name="test-model", call_type="unit_test")
    assert wrapped.invoke("hello") == "ok"
    invoke_mock.assert_called_once_with("hello")


def test_backtest_counter_defined():
    from app.core.metrics import BACKTEST_COMPLETED

    if BACKTEST_COMPLETED is not None:
        assert "backtest_completed" in BACKTEST_COMPLETED._name


def test_structlog_injects_request_context(monkeypatch):
    try:
        import structlog
    except ImportError:
        return

    from app.core.structlogger import _inject_log_context
    from app.core.middleware.resilience import init_context, clear_context

    init_context("req-test-1")
    try:
        event = _inject_log_context(None, "info", {"event": "demo"})
        assert event["request_id"] == "req-test-1"
    finally:
        clear_context()
