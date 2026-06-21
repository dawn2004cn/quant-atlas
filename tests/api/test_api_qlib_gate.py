"""ENABLE_QLIB=0 时受保护接口返回校验错误。"""

import werkzeug


def test_qlib_ingest_rejected_when_disabled(monkeypatch):
    monkeypatch.setenv("ENABLE_BACKGROUND_SCANNER", "0")
    monkeypatch.setenv("ENABLE_QLIB", "0")
    if not hasattr(werkzeug, "__version__"):
        monkeypatch.setattr(werkzeug, "__version__", "3.0.0", raising=False)
    from app.bootstrap import create_app

    app = create_app()
    app.config["TESTING"] = True
    c = app.test_client()
    assert c.post("/login", data={"username": "admin", "password": "admin123"}).status_code in (302, 303)
    r = c.post(
        "/api/v1/qlib/ingest",
        json={"symbols": ["600519"], "market": "CN"},
        content_type="application/json",
    )
    assert r.status_code == 400
    body = r.get_json()
    assert body.get("status") == "error"
    assert "ENABLE_QLIB" in (body.get("error") or {}).get("message", "")
