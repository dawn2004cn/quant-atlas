"""Unit checks for market_quotes preferred_endpoint meta / legacy dump headers (续十五/二十)."""

from __future__ import annotations

from flask import Flask


def test_ok_response_meta_carries_preferred_endpoint() -> None:
    """Smoke: success envelope keeps preferred_endpoint in meta."""
    from app.presentation.api.common import ok_response

    app = Flask(__name__)
    with app.app_context():
        resp, code = ok_response(
            data={"stocks": [], "count": 0},
            preferred_endpoint="/markets/CN/quotes/page",
            hint="use page",
            legacy_full_dump=True,
        )
        assert code == 200
        payload = resp.get_json()
        assert payload["success"] is True
        assert payload["meta"]["preferred_endpoint"] == "/markets/CN/quotes/page"
        assert payload["meta"]["hint"] == "use page"
        assert payload["meta"]["legacy_full_dump"] is True


def test_legacy_full_dump_response_headers() -> None:
    """Full-dump responses should advertise X-Preferred-Endpoint + Warning."""
    from app.presentation.api.common import ok_response

    app = Flask(__name__)
    with app.app_context():
        resp, status = ok_response(
            data={"stocks": [], "count": 0},
            preferred_endpoint="/markets/CN/quotes/page",
            legacy_full_dump=True,
            hint="use page",
        )
        assert status == 200
        preferred_api = "/api/v1/markets/CN/quotes/page"
        resp.headers["X-Preferred-Endpoint"] = preferred_api
        resp.headers["Warning"] = (
            '299 quant-atlas "Full-market /quotes dump is legacy; use quotes/page"'
        )
        assert resp.headers["X-Preferred-Endpoint"] == preferred_api
        assert "quotes/page" in resp.headers["Warning"]
