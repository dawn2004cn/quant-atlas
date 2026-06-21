from __future__ import annotations

from pathlib import Path

from flask import Flask
import werkzeug

from app.presentation.static_files import configure_static_files

if not hasattr(werkzeug, "__version__"):
    werkzeug.__version__ = "3.0.0"


def _app(tmp_path):
    static_root = tmp_path / "static"
    static_root.mkdir()
    app = Flask(__name__, static_folder=str(static_root), static_url_path="/static")
    configure_static_files(app, static_root)
    return app


def test_upload_path_traversal_returns_403(tmp_path):
    app = _app(tmp_path)

    client = app.test_client()
    response = client.get("/uploads/../static_files.py")

    assert response.status_code == 403


def test_upload_percent_encoded_traversal_returns_403(tmp_path):
    app = _app(tmp_path)

    client = app.test_client()
    response = client.get("/uploads/%2e%2e/static_files.py")

    assert response.status_code == 403


def test_upload_serves_only_files_under_uploads(tmp_path):
    app = _app(tmp_path)
    uploads_dir = Path(app.instance_path) / "uploads"
    uploads_dir.mkdir(parents=True, exist_ok=True)
    (uploads_dir / "safe.txt").write_text("ok", encoding="utf-8")

    response = app.test_client().get("/uploads/safe.txt")

    assert response.status_code == 200
    assert response.get_data(as_text=True) == "ok"
