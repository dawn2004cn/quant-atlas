"""MLflow ModelRegistry helpers."""

from __future__ import annotations

from app.infrastructure.mlflow.registry import ModelRegistry


def test_build_run_ui_url_with_tracking_uri(monkeypatch):
    monkeypatch.setattr(
        "app.infrastructure.mlflow.registry.get_runtime",
        lambda key, default="": "http://mlflow.local:5000"
        if key == "MLFLOW_TRACKING_URI"
        else default,
    )
    url = ModelRegistry.build_run_ui_url("abc123", "7")
    assert url == "http://mlflow.local:5000/#/experiments/7/runs/abc123"


def test_build_run_ui_url_missing_tracking_uri(monkeypatch):
    monkeypatch.setattr(
        "app.infrastructure.mlflow.registry.get_runtime",
        lambda _key, default="": default,
    )
    assert ModelRegistry.build_run_ui_url("abc123", "7") is None


def test_get_tracking_config(monkeypatch):
    monkeypatch.setattr(
        "app.infrastructure.mlflow.registry.ModelRegistry.is_available",
        staticmethod(lambda: False),
    )
    monkeypatch.setattr(
        "app.infrastructure.mlflow.registry.get_runtime",
        lambda key, default="": {
            "MLFLOW_TRACKING_URI": "http://mlflow:5000",
            "MLFLOW_EXPERIMENT": "exp-a",
            "MLFLOW_REGISTER_MODELS": "1",
        }.get(key, default),
    )
    cfg = ModelRegistry.get_tracking_config()
    assert cfg["available"] is False
    assert cfg["tracking_uri"] == "http://mlflow:5000"
    assert cfg["experiment"] == "exp-a"
    assert cfg["register_models"] is True
