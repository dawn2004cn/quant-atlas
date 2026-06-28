"""Page routes: market domain. Split from pages.py."""

from __future__ import annotations

from flask import (
    Blueprint,
    render_template,
    url_for,
)
from flask_login import current_user, login_required

from app.modules.system.services.integration.integration_hub_service import (
    build_integration_hub_context,
)
from app.config import get_settings
from app.models import STRATEGY_REGISTRY_GROUPS
from app.presentation.web.page_shell import ux_env_hints as _ux_env_hints

def register_pages(blueprint: Blueprint) -> None:
    @blueprint.route("/")
    @login_required
    def daily_workbench():
        settings = get_settings()
        return render_template(
            "daily_workbench.html",
            username=current_user.username,
            ux_env_hints=_ux_env_hints(settings),
        )

    @blueprint.route("/dashboard")
    @login_required
    def dashboard():
        return render_template("index.html", username=current_user.username)

    @blueprint.route("/capabilities")
    @login_required
    def capabilities():
        settings = get_settings()
        return render_template(
            "capabilities.html",
            enable_qlib=settings.enable_qlib,
            enable_celery=settings.enable_celery,
            enable_rd_agent=settings.enable_rd_agent,
            ux_env_hints=_ux_env_hints(settings),
        )

    @blueprint.route("/integration-hub")
    @login_required
    def integration_hub():
        settings = get_settings()
        ctx = build_integration_hub_context(settings=settings)
        return render_template(
            "integration_hub.html",
            **ctx,
            ux_env_hints=_ux_env_hints(settings),
        )

    @blueprint.route("/market-panorama")
    @login_required
    def market_panorama():
        settings = get_settings()
        return render_template("market_panorama.html", ux_env_hints=_ux_env_hints(settings))

    @blueprint.route("/global-radar")
    @login_required
    def global_radar():
        settings = get_settings()
        return render_template("global_radar.html", ux_env_hints=_ux_env_hints(settings))

    @blueprint.route("/market-panorama/<market>")
    @login_required
    def market_panorama_by_market(market: str):
        settings = get_settings()
        return render_template(
            "market_panorama.html",
            market=market.upper(),
            ux_env_hints=_ux_env_hints(settings),
        )

    @blueprint.route("/tdx-blocks")
    @login_required
    def tdx_blocks():
        settings = get_settings()
        return render_template("tdx_blocks.html", ux_env_hints=_ux_env_hints(settings))

    @blueprint.route("/backtest")
    @login_required
    def backtest():
        settings = get_settings()
        return render_template(
            "backtest.html",
            strategy_groups=STRATEGY_REGISTRY_GROUPS,
            enable_qlib=settings.enable_qlib,
            ux_env_hints=_ux_env_hints(settings),
        )

    @blueprint.route("/observability")
    @login_required
    def observability():
        settings = get_settings()
        return render_template(
            "observability.html",
            ux_env_hints=_ux_env_hints(settings),
        )

    @blueprint.route("/hot-sectors")
    @login_required
    def hot_sectors():
        settings = get_settings()
        return render_template("hot_sectors.html", ux_env_hints=_ux_env_hints(settings))

    @blueprint.route("/architecture-roadmap")
    @login_required
    def architecture_roadmap():
        return render_template("architecture_roadmap.html")

    @blueprint.route("/ui-showcase")
    @blueprint.route("/ui-showcase/dark")
    @login_required
    def ui_showcase_dark():
        return render_template(
            "ui_showcase.html",
            ui_theme="dark",
            alternate_theme_url=url_for("pages.ui_showcase_light"),
        )

    @blueprint.route("/ui-showcase/light")
    @login_required
    def ui_showcase_light():
        return render_template(
            "ui_showcase.html",
            ui_theme="light",
            alternate_theme_url=url_for("pages.ui_showcase_dark"),
        )


