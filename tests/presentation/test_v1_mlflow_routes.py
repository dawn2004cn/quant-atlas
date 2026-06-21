"""MLflow v1 API routes."""

from __future__ import annotations

import werkzeug
from flask import Flask
from flask_login import LoginManager

from app.infrastructure.mlflow.registry import ModelRegistry
from app.presentation.api.routes_v1_mlflow import register_mlflow_routes
from app.presentation.api.v1_context import ApiV1Context

if not hasattr(werkzeug, "__version__"):
    werkzeug.__version__ = "3.0.0"


class _User:
    id = 1
    username = "admin"
    is_authenticated = True


def _app_with_mlflow_routes(monkeypatch):
    monkeypatch.setattr(
        "app.infrastructure.mlflow.registry.ModelRegistry.is_available",
        staticmethod(lambda: True),
    )
    monkeypatch.setattr(
        "app.infrastructure.mlflow.registry.ModelRegistry.list_recent_runs",
        staticmethod(lambda max_results=20: [{"run_id": "run-1", "run_name": "MA-600519"}]),
    )
    monkeypatch.setattr(
        "app.infrastructure.mlflow.registry.ModelRegistry.get_run",
        staticmethod(lambda run_id: {"run_id": run_id, "run_name": "demo", "metrics": {"sharpe": 1.1}}),
    )
    monkeypatch.setattr(
        "app.infrastructure.mlflow.registry.ModelRegistry.list_registered_models",
        staticmethod(
            lambda max_results=20: [
                {"name": "ma_model", "version": "1", "stage": "Production", "run_id": "run-1"}
            ]
        ),
    )

    app = Flask(__name__)
    app.secret_key = "test"
    lm = LoginManager(app)

    @lm.user_loader
    def load_user(_user_id):
        return _User()

    bp = __import__("flask").Blueprint("api_v1", __name__, url_prefix="/api/v1")
    register_mlflow_routes(bp, ApiV1Context())
    app.register_blueprint(bp)
    return app


def test_mlflow_runs_list(monkeypatch):
    app = _app_with_mlflow_routes(monkeypatch)
    with app.test_client() as client:
        with client.session_transaction() as sess:
            sess["_user_id"] = "1"
        resp = client.get("/api/v1/mlflow/runs?limit=5")
        assert resp.status_code == 200
        data = resp.get_json()["data"]
        assert data["count"] == 1
        assert data["runs"][0]["run_id"] == "run-1"


def test_mlflow_run_detail(monkeypatch):
    app = _app_with_mlflow_routes(monkeypatch)
    with app.test_client() as client:
        with client.session_transaction() as sess:
            sess["_user_id"] = "1"
        resp = client.get("/api/v1/mlflow/runs/run-abc")
        assert resp.status_code == 200
        assert resp.get_json()["data"]["run"]["run_id"] == "run-abc"


def test_mlflow_registered_models(monkeypatch):
    app = _app_with_mlflow_routes(monkeypatch)
    with app.test_client() as client:
        with client.session_transaction() as sess:
            sess["_user_id"] = "1"
        resp = client.get("/api/v1/mlflow/models?limit=5")
        assert resp.status_code == 200
        data = resp.get_json()["data"]
        assert data["count"] == 1
        assert data["models"][0]["name"] == "ma_model"


def test_mlflow_status(monkeypatch):
    monkeypatch.setattr(
        "app.infrastructure.mlflow.registry.ModelRegistry.get_tracking_config",
        staticmethod(
            lambda: {
                "available": True,
                "tracking_uri": "http://mlflow:5000",
                "experiment": "quant-atlas-backtest",
                "register_models": False,
            }
        ),
    )
    app = Flask(__name__)
    app.secret_key = "test"
    lm = LoginManager(app)

    @lm.user_loader
    def load_user(_user_id):
        return _User()

    bp = __import__("flask").Blueprint("api_v1", __name__, url_prefix="/api/v1")
    register_mlflow_routes(bp, ApiV1Context())
    app.register_blueprint(bp)

    with app.test_client() as client:
        with client.session_transaction() as sess:
            sess["_user_id"] = "1"
        resp = client.get("/api/v1/mlflow/status")
        assert resp.status_code == 200
        data = resp.get_json()["data"]
        assert data["available"] is True
        assert data["tracking_uri"] == "http://mlflow:5000"
        assert data["register_models"] is False


def test_mlflow_run_detail_includes_linked_proposals(monkeypatch, tmp_path):
    from app.core.mesh.alpha_governance import AlphaGovernanceDAO

    dao = AlphaGovernanceDAO(vote_history_path=tmp_path / "votes.jsonl")
    dao.submit_proposal(
        "ma_v1",
        "trader",
        "close/open-1",
        "zk",
        {"sharpe": 1.2},
        mlflow_run_id="run-abc",
    )
    monkeypatch.setattr(
        "app.presentation.api.routes_v1_mlflow.get_alpha_governance",
        lambda: dao,
    )
    monkeypatch.setattr(
        "app.infrastructure.mlflow.registry.ModelRegistry.is_available",
        staticmethod(lambda: True),
    )
    monkeypatch.setattr(
        "app.infrastructure.mlflow.registry.ModelRegistry.get_run",
        staticmethod(
            lambda run_id: {
                "run_id": run_id,
                "run_name": "demo",
                "metrics": {"sharpe": 1.1},
            }
        ),
    )

    app = Flask(__name__)
    app.secret_key = "test"
    lm = LoginManager(app)

    @lm.user_loader
    def load_user(_user_id):
        return _User()

    bp = __import__("flask").Blueprint("api_v1", __name__, url_prefix="/api/v1")
    register_mlflow_routes(bp, ApiV1Context())
    app.register_blueprint(bp)

    with app.test_client() as client:
        with client.session_transaction() as sess:
            sess["_user_id"] = "1"
        resp = client.get("/api/v1/mlflow/runs/run-abc")
        assert resp.status_code == 200
        data = resp.get_json()["data"]
        assert data["run"]["run_id"] == "run-abc"
        assert len(data["linked_proposals"]) == 1
        assert data["linked_proposals"][0]["mlflow_run_id"] == "run-abc"


def test_mlflow_run_detail_not_found(monkeypatch):
    monkeypatch.setattr(
        "app.infrastructure.mlflow.registry.ModelRegistry.is_available",
        staticmethod(lambda: True),
    )
    monkeypatch.setattr(
        "app.infrastructure.mlflow.registry.ModelRegistry.get_run",
        staticmethod(lambda _run_id: None),
    )

    app = Flask(__name__)
    app.secret_key = "test"
    lm = LoginManager(app)

    @lm.user_loader
    def load_user(_user_id):
        return _User()

    bp = __import__("flask").Blueprint("api_v1", __name__, url_prefix="/api/v1")
    register_mlflow_routes(bp, ApiV1Context())
    app.register_blueprint(bp)

    with app.test_client() as client:
        with client.session_transaction() as sess:
            sess["_user_id"] = "1"
        resp = client.get("/api/v1/mlflow/runs/missing")
        assert resp.status_code != 200
