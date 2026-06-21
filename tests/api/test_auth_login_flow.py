"""Flask-Login 会话链路：登录后首页须能渲染（依赖 SessionUser）。"""

import werkzeug


def test_login_post_then_dashboard_has_username(monkeypatch):
    monkeypatch.setenv("ENABLE_BACKGROUND_SCANNER", "0")
    # Flask 2.0.x test_client 依赖 werkzeug.__version__，新版 Werkzeug 已移除该属性
    if not hasattr(werkzeug, "__version__"):
        monkeypatch.setattr(werkzeug, "__version__", "3.0.0", raising=False)
    from app.bootstrap import create_app

    app = create_app()
    app.config["TESTING"] = True
    client = app.test_client()
    resp = client.post(
        "/login",
        data={"username": "admin", "password": "admin123"},
        follow_redirects=False,
    )
    assert resp.status_code in (302, 303)
    home = client.get("/", follow_redirects=False)
    assert home.status_code == 200
    # base.html user-chip 展示 current_user.username
    assert b"admin" in home.data
