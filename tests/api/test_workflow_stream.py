"""Tests for Phase 10 Directive 4: workflow stream/log endpoint."""
from __future__ import annotations

import json


def test_workflow_status_returns_json_structure():
    from app.presentation.api.routes_v1_workflows import register_workflow_routes
    from app.presentation.api.v1_context import ApiV1Context
    from flask import Flask

    app = Flask(__name__)
    blueprint = Flask(__name__)

    class _FakeWF:
        def get_status(self, workflow_id):
            return {"workflow_id": workflow_id, "status": "running"}

        def get_evidence(self, workflow_id):
            return [{"step": "scan", "ok": True}]

    register_workflow_routes(blueprint, ApiV1Context(workflow_service=_FakeWF()))

    with app.test_client() as client:
        resp = client.get("/workflows/test-123")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "status" in data
        assert "evidence" in data


def test_workflow_list_endpoint():
    from app.presentation.api.routes_v1_workflows import register_workflow_routes
    from app.presentation.api.v1_context import ApiV1Context
    from flask import Flask

    app = Flask(__name__)
    blueprint = Flask(__name__)

    class _FakeWF:
        def list_workflows(self):
            return [{"workflow_id": "wf-1", "status": "running"}]

    register_workflow_routes(blueprint, ApiV1Context(workflow_service=_FakeWF()))

    with app.test_client() as client:
        resp = client.get("/workflows")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "workflows" in data
        assert len(data["workflows"]) == 1
