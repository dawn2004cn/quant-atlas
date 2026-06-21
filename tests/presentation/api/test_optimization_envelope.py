"""Optimization route canonical envelope tests."""
from __future__ import annotations

import json

from app.presentation.api.responses import success_response
from tests.helpers import create_test_app


def test_budget_validate_wiring_envelope_shape():
    app = create_test_app()
    wiring_result = {"factory_count": 42, "ok": True, "checked": 3}

    with app.app_context():
        resp, status = success_response(data=wiring_result)

    assert status == 200
    body = json.loads(resp.get_data(as_text=True))
    assert body["success"] is True
    assert body["ok"] is True
    assert body["status"] == "success"
    assert body["data"]["factory_count"] == 42
    assert body["error"] is None
