"""Alpha governance v1 API routes."""

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


def test_alpha_governance_proposal_and_vote(monkeypatch, tmp_path):
    dao = AlphaGovernanceDAO(vote_history_path=tmp_path / "votes.jsonl")
    monkeypatch.setattr(
        "app.presentation.api.routes_v1_alpha_governance.get_alpha_governance",
        lambda: dao,
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

        stats_resp = client.get("/api/v1/alpha/governance/stats")
        assert stats_resp.status_code == 200
        stats = stats_resp.get_json()["data"]["stats"]
        assert stats["proposals"] == 0
        assert "thresholds" in stats
        assert stats["thresholds"]["majority"] == 0.6
        assert stats["thresholds"]["quorum"] == 0.5

        create_resp = client.post(
            "/api/v1/alpha/governance/proposals",
            json={
                "strategy_id": "mom_v1",
                "expression": "close / open - 1",
                "performance_metrics": {"sharpe": 1.1},
            },
        )
        assert create_resp.status_code == 200
        proposal_id = create_resp.get_json()["data"]["proposal_id"]
        assert proposal_id

        vote_resp = client.post(
            "/api/v1/alpha/governance/vote",
            json={"proposal_id": proposal_id, "approve": True, "rationale": "ok"},
        )
        assert vote_resp.status_code == 200
        assert vote_resp.get_json()["data"]["tally"]["votes_for"] == 1

        votes_resp = client.get(f"/api/v1/alpha/governance/votes?proposal_id={proposal_id}")
        assert votes_resp.status_code == 200
        assert len(votes_resp.get_json()["data"]["votes"]) == 1

        list_resp = client.get("/api/v1/alpha/governance/proposals")
        assert list_resp.status_code == 200
        assert len(list_resp.get_json()["data"]["proposals"]) == 1


def test_submit_proposal_with_lineage_ids(tmp_path):
    dao = AlphaGovernanceDAO(
        vote_history_path=tmp_path / "votes.jsonl",
        proposal_store_path=tmp_path / "proposals.json",
    )
    pid = dao.submit_proposal(
        "bt_ma",
        "trader",
        "close/open-1",
        "zk",
        {"sharpe": 1.2},
        mlflow_run_id="run-abc123",
        mining_factor_id="factor-xyz",
    )
    row = dao.get_proposal(pid)
    assert row is not None
    assert row["mlflow_run_id"] == "run-abc123"
    assert row["mining_factor_id"] == "factor-xyz"
    listed = dao.list_proposals()
    assert listed[0]["mlflow_run_id"] == "run-abc123"

    reloaded = AlphaGovernanceDAO(
        vote_history_path=tmp_path / "votes.jsonl",
        proposal_store_path=tmp_path / "proposals.json",
    )
    detail = reloaded.get_proposal(pid)
    assert detail is not None
    assert detail["mining_factor_id"] == "factor-xyz"


def test_alpha_governance_proposal_api_accepts_lineage(monkeypatch, tmp_path):
    dao = AlphaGovernanceDAO(vote_history_path=tmp_path / "votes.jsonl")
    monkeypatch.setattr(
        "app.presentation.api.routes_v1_alpha_governance.get_alpha_governance",
        lambda: dao,
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

        create_resp = client.post(
            "/api/v1/alpha/governance/proposals",
            json={
                "strategy_id": "mom_v1",
                "expression": "close / open - 1",
                "performance_metrics": {"sharpe": 1.1},
                "mlflow_run_id": "mlf-001",
                "mining_factor_id": "fac-001",
            },
        )
        assert create_resp.status_code == 200
        proposal = create_resp.get_json()["data"]["proposal"]
        assert proposal["mlflow_run_id"] == "mlf-001"
        assert proposal["mining_factor_id"] == "fac-001"


def test_list_proposals_and_get_proposal(tmp_path):
    dao = AlphaGovernanceDAO(vote_history_path=tmp_path / "votes.jsonl")
    pid = dao.submit_proposal("s1", "m1", "x+y", "zk", {"sharpe": 1.0})
    dao.vote(pid, "team-x", True)
    rows = dao.list_proposals()
    assert rows[0]["proposal_id"] == pid
    detail = dao.get_proposal(pid)
    assert detail is not None
    assert len(detail["vote_history"]) == 1
    assert detail["tally"]["votes_for"] == 1
    assert len(detail["timeline"]) >= 2
    assert detail["timeline"][0]["type"] == "submitted"


def test_find_proposals_by_mlflow_run(tmp_path):
    dao = AlphaGovernanceDAO(vote_history_path=tmp_path / "votes.jsonl")
    pid = dao.submit_proposal(
        "s1",
        "m1",
        "x+y",
        "zk",
        {"sharpe": 1.0},
        mlflow_run_id="run-link-1",
    )
    matches = dao.find_proposals_by_mlflow_run("run-link-1")
    assert len(matches) == 1
    assert matches[0]["proposal_id"] == pid
    assert dao.find_proposals_by_mlflow_run("missing") == []
