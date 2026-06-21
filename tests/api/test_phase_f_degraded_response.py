"""Phase F: degraded_response 单测."""
from __future__ import annotations

from flask import Flask, Response

from app.presentation.api.degraded_response import (
    SelfHealingDomainError,
    apply_degraded_headers,
)


def _resp():
    return Response("ok")


def test_apply_degraded_headers_adds_degraded_tag():
    app = Flask(__name__)
    with app.app_context():
        err = SelfHealingDomainError(
            "mysql_fallback",
            degraded_tag="mysql_fallback",
        )
        resp = apply_degraded_headers(_resp(), err)
        assert resp.headers.get("X-QC-Degraded") == "mysql_fallback"


def test_apply_degraded_headers_adds_hints():
    app = Flask(__name__)
    with app.app_context():
        err = SelfHealingDomainError(
            "hint",
            hints=[{"action_label": "retry", "action_href": "/tasks"}],
        )
        resp = apply_degraded_headers(_resp(), err)
        import json

        raw = resp.headers.get("X-QC-Hints")
        assert raw is not None
        hints = json.loads(raw)
        assert hints[0]["action_label"] == "retry"


def test_apply_degraded_headers_skips_plain_exception():
    app = Flask(__name__)
    with app.app_context():
        resp = apply_degraded_headers(_resp(), ValueError("plain"))
        assert "X-QC-Degraded" not in resp.headers
        assert "X-QC-Hints" not in resp.headers


def test_self_healing_domain_error_defaults():
    err = SelfHealingDomainError("msg")
    assert err.CODE == "SELF_HEALING_DOMAIN_ERROR"
    assert err.STATUS_CODE == 400
    assert err.hints == []
    assert err.degraded_tag is None
