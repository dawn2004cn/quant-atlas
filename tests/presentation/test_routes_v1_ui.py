from __future__ import annotations

from unittest.mock import MagicMock

from app.presentation.api.routes_v1_ui import register_ui_routes


def test_capabilities_registry_includes_team_components() -> None:
    captured: dict = {}

    class _Bp:
        def get(self, path):
            def deco(fn):
                captured[path] = fn
                return fn

            return deco

    ctx = MagicMock()
    ctx.enable_legacy_response_fields = False
    register_ui_routes(_Bp(), ctx)  # type: ignore[arg-type]
    fn = captured["/ui/capabilities"]

    class _User:
        is_authenticated = True
        id = 1

    from flask import Flask
    from flask_login import LoginManager

    app = Flask(__name__)
    app.config["SECRET_KEY"] = "test"
    lm = LoginManager(app)

    class U:
        id = 1
        is_authenticated = True
        is_active = True

        def get_id(self) -> str:
            return str(self.id)

    @lm.user_loader
    def _load(_id):
        return U()

    with app.test_request_context():
        from flask_login import login_user

        login_user(U())
        resp = fn()
        body = resp.get_json()
        data = body.get("data") or body
        assert "team-blackboard" in data["stock_detail"]
        assert "team-research-feed" in data["collaboration_workspace"]
