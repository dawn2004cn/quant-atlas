from app import create_app


def test_create_app_exposes_bootstrap_bundles(monkeypatch):
    monkeypatch.setenv("ENABLE_BACKGROUND_SCANNER", "0")
    monkeypatch.setenv("ENABLE_BASIC_DATA_SCHEDULER", "0")
    monkeypatch.setenv("ENABLE_CELERY", "0")
    monkeypatch.setenv("ENABLE_QLIB", "0")
    monkeypatch.setenv("ENABLE_RD_AGENT", "0")
    monkeypatch.setenv("TASK_MESSAGE_REDIS_URL", "memory://")

    app = create_app()

    assert "repository_bundle" in app.extensions
    assert "provider_bundle" in app.extensions
    assert "service_bundle" in app.extensions
    assert app.config["BACKGROUND_POLICY"] == {
        "enabled": False,
        "services": [],
    }

