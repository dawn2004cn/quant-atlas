"""Governance workbench API."""

from __future__ import annotations

import werkzeug
from flask import Flask
from flask_login import LoginManager

from app.core.mesh.alpha_governance import AlphaGovernanceDAO
from app.presentation.api.routes_v1_alpha_governance import register_alpha_governance_routes
from app.presentation.api.v1_context import ApiV1Context

if not hasattr(werkzeug, "__version__"):
    werkzeug.__version__ = "3.0.0"


class _User:
    id = 1
    username = "admin"
    is_authenticated = True


def test_alpha_governance_workbench(monkeypatch, tmp_path):
    dao = AlphaGovernanceDAO(
        vote_history_path=tmp_path / "votes.jsonl",
        proposal_store_path=tmp_path / "proposals.json",
    )
    dao.submit_proposal("s1", "m1", "x+y", "zk", {"sharpe": 1.0})
    monkeypatch.setattr(
        "app.presentation.api.routes_v1_alpha_governance.get_alpha_governance",
        lambda: dao,
    )
    monkeypatch.setattr(
        "app.presentation.api.routes_v1_alpha_governance.ModelRegistry.is_available",
        staticmethod(lambda: False),
    )
    monkeypatch.setattr(
        "app.presentation.api.routes_v1_alpha_governance.ModelRegistry.list_recent_runs",
        staticmethod(lambda max_results=10: []),
    )

    class _Mining:
        @staticmethod
        def list_discovered_factors(**_kwargs):
            return [{"factor_id": "f-1", "expression": "rank(close)", "sharpe": 1.1}]

    monkeypatch.setattr(
        "app.modules.strategy.services.alpha_mining_service.AutoAlphaMiningService",
        _Mining,
    )

    app = Flask(__name__)
    app.secret_key = "test"
    lm = LoginManager(app)

    @lm.user_loader
    def load_user(_user_id):
        return _User()

    bp = __import__("flask").Blueprint("api_v1", __name__, url_prefix="/api/v1")
    register_alpha_governance_routes(bp, ApiV1Context())
    app.register_blueprint(bp)

    with app.test_client() as client:
        with client.session_transaction() as sess:
            sess["_user_id"] = "1"
        resp = client.get("/api/v1/alpha/governance/workbench?limit=5")

    assert resp.status_code == 200
    body = resp.get_json()["data"]
    assert len(body["proposals"]) == 1
    assert body["mining_factors"][0]["factor_id"] == "f-1"
    assert body["mlflow"]["available"] is False
