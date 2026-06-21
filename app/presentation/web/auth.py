"""Authentication blueprint with rate limiting."""

from __future__ import annotations

import secrets
import time
from typing import TYPE_CHECKING

from flask import Blueprint, flash, redirect, render_template, request, session, url_for, current_app
from flask_login import current_user, login_required, login_user, logout_user
from markupsafe import escape

from ...infrastructure.external.wechat_web_login import (
    build_qrconnect_url,
    exchange_code,
    fetch_sns_userinfo,
)
from ...infrastructure.auth.oauth_provider import extract_subject_from_token_response
from ...core.runtime_config import get_runtime
from ...core.hybrid_rate_limiter import HybridRateLimiter
from .models import SessionUser

if TYPE_CHECKING:
    from ...application.services.auth_service import AuthService
    from ...application.services.user_service import UserApplicationService
    from ...config import AppSettings
    from ...domain.ports.oauth_port import OAuthProviderPort


# ---------------------------------------------------------------------------
# Auth rate limiting (Redis when available, in-memory fallback)
# ---------------------------------------------------------------------------
_LOGIN_RATE_WINDOW = 60
_LOGIN_RATE_MAX_ATTEMPTS = 5
_login_limiter = HybridRateLimiter(
    "auth_login",
    window=_LOGIN_RATE_WINDOW,
    max_attempts=_LOGIN_RATE_MAX_ATTEMPTS,
)
_register_limiter = HybridRateLimiter("auth_register", window=3600, max_attempts=10)


def create_auth_blueprint(
    auth_service: "AuthService" = None,
    user_service: "UserApplicationService" = None,
    *,
    app_settings: "AppSettings" = None,
    oauth_provider: "OAuthProviderPort | None" = None,
):
    """Build auth routes (注册、微信扫码、账号密码登录)。"""
    if auth_service is None or user_service is None or app_settings is None:
        return None

    blueprint = Blueprint("auth", __name__)

    def _wechat_redirect_base() -> str:
        u = (app_settings.wechat_redirect_uri or "").strip()
        if u:
            return u.rstrip("/")
        return request.url_root.rstrip("/")

    def _oauth_redirect_base() -> str:
        u = get_runtime("OAUTH_REDIRECT_URI", "").strip()
        if u:
            return u.rstrip("/")
        return request.url_root.rstrip("/")

    def _oauth_available() -> bool:
        return oauth_provider is not None and oauth_provider.is_configured()

    def _login_locked_seconds(ip_key: str) -> int:
        if current_app.config.get("TESTING", False):
            return 0
        if not _login_limiter.is_blocked(ip_key):
            return 0
        return _login_limiter.retry_after(ip_key)

    def _render_login(
        *,
        wechat_login_available: bool,
        oauth_login_available: bool,
        login_locked_seconds: int = 0,
    ):
        return render_template(
            "login.html",
            wechat_login_available=wechat_login_available,
            oauth_login_available=oauth_login_available,
            login_locked_seconds=login_locked_seconds,
            login_rate_window=_LOGIN_RATE_WINDOW,
        )

    @blueprint.route("/login", methods=["GET", "POST"])
    def login():
        ip_key = request.remote_addr or "unknown"
        wx_ok = bool(
            app_settings.wechat_open_app_id
            and app_settings.wechat_open_app_secret,
        )
        oauth_ok = _oauth_available()

        if request.method == "POST":
            locked_seconds = _login_locked_seconds(ip_key)
            if locked_seconds > 0:
                return _render_login(
                    wechat_login_available=wx_ok,
                    oauth_login_available=oauth_ok,
                    login_locked_seconds=locked_seconds,
                )

            username = request.form.get("username", "").strip()
            password = request.form.get("password", "")
            user = auth_service.authenticate(username, password)
            if user:
                if not current_app.config.get("TESTING", False):
                    _login_limiter.reset(ip_key)
                # Prevent session fixation: rotate session ID on successful login
                session.clear()
                session["_user_id"] = str(user.user_id)
                session["_username"] = user.username
                session["_fresh"] = True
                session["_session_created"] = time.time()
                remember = request.form.get("remember_me") == "on"
                login_user(SessionUser.from_entity(user), remember=remember)
                return redirect(url_for("pages.dashboard"))

            if not current_app.config.get("TESTING", False):
                _login_limiter.record(ip_key)
            flash("用户名或密码错误", "error")
            return _render_login(
                wechat_login_available=wx_ok,
                oauth_login_available=oauth_ok,
                login_locked_seconds=_login_locked_seconds(ip_key),
            )

        return _render_login(
            wechat_login_available=wx_ok,
            oauth_login_available=oauth_ok,
            login_locked_seconds=_login_locked_seconds(ip_key),
        )

    @blueprint.route("/register", methods=["GET", "POST"])
    def register():
        ip_key = request.remote_addr or "unknown"
        if not _register_limiter.allow(ip_key):
            flash("注册尝试过于频繁，请稍后再试", "error")
            return render_template("register.html")

        if current_user.is_authenticated:
            return redirect(url_for("pages.dashboard"))
        if request.method == "POST":
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "")
            confirm = request.form.get("confirm_password", "")
            if password != confirm:
                flash("两次输入的密码不一致", "error")
            else:
                ok, msg = user_service.register_public(username, password)
                if ok:
                    flash(msg, "success")
                    return redirect(url_for("auth.login"))
                flash(msg, "error")
        return render_template("register.html")

    @blueprint.route("/auth/wechat/start")
    def wechat_start():
        if not app_settings.wechat_open_app_id or not app_settings.wechat_open_app_secret:
            flash("微信扫码登录未配置（需 WECHAT_OPEN_APP_ID / WECHAT_OPEN_APP_SECRET）", "error")
            return redirect(url_for("auth.login"))
        state = secrets.token_urlsafe(24)
        session["wx_oauth_state"] = state
        cb = f"{_wechat_redirect_base()}/auth/wechat/callback"
        url = build_qrconnect_url(
            app_id=app_settings.wechat_open_app_id,
            redirect_uri=cb,
            state=state,
        )
        return redirect(url)

    @blueprint.route("/auth/wechat/callback")
    def wechat_callback():
        if session.get("wx_oauth_state") != request.args.get("state"):
            flash("登录状态校验失败，请重新扫码", "error")
            return redirect(url_for("auth.login"))
        session.pop("wx_oauth_state", None)
        code = (request.args.get("code") or "").strip()
        if not code:
            err = (request.args.get("error_description") or request.args.get("error") or "").strip()
            flash(err or "未收到微信授权码", "error")
            return redirect(url_for("auth.login"))
        if not app_settings.wechat_open_app_id or not app_settings.wechat_open_app_secret:
            flash("微信登录未配置", "error")
            return redirect(url_for("auth.login"))
        tok = exchange_code(
            app_settings.wechat_open_app_id,
            app_settings.wechat_open_app_secret,
            code,
        )
        if not tok:
            flash("换取微信 access_token 失败", "error")
            return redirect(url_for("auth.login"))
        openid = str(tok.get("openid") or "").strip()
        if not openid:
            flash("微信未返回 openid", "error")
            return redirect(url_for("auth.login"))
        nickname = None
        at = tok.get("access_token")
        if at and openid:
            info = fetch_sns_userinfo(str(at), openid)
            if isinstance(info, dict):
                nickname = str(info.get("nickname") or "").strip() or None
        user = user_service.provision_wechat_user(openid, nickname=nickname)
        if not user:
            flash("创建或关联微信用户失败", "error")
            return redirect(url_for("auth.login"))
        # Prevent session fixation on OAuth login
        session.clear()
        session["_user_id"] = str(user.user_id)
        session["_username"] = user.username
        session["_fresh"] = True
        session["_session_created"] = time.time()
        login_user(SessionUser.from_entity(user), remember=True)
        return redirect(url_for("pages.dashboard"))

    @blueprint.route("/auth/oauth/start")
    def oauth_start():
        if not _oauth_available():
            flash("OAuth 登录未配置（需 KEYCLOAK_* 环境变量）", "error")
            return redirect(url_for("auth.login"))
        state = secrets.token_urlsafe(24)
        session["oauth_state"] = state
        cb = f"{_oauth_redirect_base()}/auth/oauth/callback"
        url = oauth_provider.authorization_url(redirect_uri=cb, state=state)
        return redirect(url)

    @blueprint.route("/auth/oauth/callback")
    def oauth_callback():
        if not _oauth_available():
            flash("OAuth 登录未配置", "error")
            return redirect(url_for("auth.login"))
        if session.get("oauth_state") != request.args.get("state"):
            flash("登录状态校验失败，请重新登录", "error")
            return redirect(url_for("auth.login"))
        session.pop("oauth_state", None)
        code = (request.args.get("code") or "").strip()
        if not code:
            err = (request.args.get("error_description") or request.args.get("error") or "").strip()
            flash(err or "未收到 OAuth 授权码", "error")
            return redirect(url_for("auth.login"))
        cb = f"{_oauth_redirect_base()}/auth/oauth/callback"
        try:
            tokens = oauth_provider.exchange_code(code=code, redirect_uri=cb)
        except Exception:
            flash("OAuth 换取令牌失败", "error")
            return redirect(url_for("auth.login"))
        sub, display_name = extract_subject_from_token_response(oauth_provider, tokens)
        if not sub:
            flash("OAuth 未返回有效用户标识", "error")
            return redirect(url_for("auth.login"))
        user = user_service.provision_oauth_user(sub, display_name=display_name)
        if not user:
            flash("创建或关联 OAuth 用户失败", "error")
            return redirect(url_for("auth.login"))
        # Prevent session fixation on OAuth login
        session.clear()
        session["_user_id"] = str(user.user_id)
        session["_username"] = user.username
        session["_fresh"] = True
        session["_session_created"] = time.time()
        login_user(SessionUser.from_entity(user), remember=True)
        return redirect(url_for("pages.dashboard"))

    @blueprint.route("/logout")
    @login_required
    def logout():
        logout_user()
        return redirect(url_for("auth.login"))

    return blueprint
