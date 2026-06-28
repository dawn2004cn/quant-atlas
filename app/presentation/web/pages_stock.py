"""Page routes: stock domain. Split from pages.py."""

from __future__ import annotations

from flask import (
    Blueprint,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import login_required

from app.config import get_settings
from app.presentation.web.page_shell import render_page_shell
from app.presentation.web.page_shell import ux_env_hints as _ux_env_hints


def register_pages(blueprint: Blueprint) -> None:
    @blueprint.route("/stock/<symbol>")
    @login_required
    def stock_detail(symbol: str):
        market = request.args.get("m", "").strip().upper() or None
        return render_page_shell(
            "stock_detail.html",
            code=symbol,
            stock_market=market,
        )

    @blueprint.route("/detail/<symbol>")
    @login_required
    def legacy_stock_detail(symbol: str):
        return redirect(url_for("pages.stock_detail", symbol=symbol))

    @blueprint.route("/strategy-compare")
    @login_required
    def strategy_compare():
        settings = get_settings()
        return render_template("strategy_compare.html", ux_env_hints=_ux_env_hints(settings))

    @blueprint.route("/attribution-dashboard")
    @login_required
    def attribution_dashboard():
        return render_template("attribution_dashboard.html")

    @blueprint.route("/strategy-snapshots")
    @login_required
    def strategy_snapshots():
        settings = get_settings()
        return render_template("strategy_snapshots.html", ux_env_hints=_ux_env_hints(settings))

    @blueprint.route("/decision-snapshot/<snapshot_id>")
    @login_required
    def decision_snapshot(snapshot_id: str):
        settings = get_settings()
        return render_template("decision_snapshot.html", snapshot_id=snapshot_id, ux_env_hints=_ux_env_hints(settings))

    @blueprint.route("/share/decision/<share_token>")
    def decision_snapshot_public(share_token: str):
        get_settings()
        return render_template("decision_snapshot_public.html", share_token=share_token)

    @blueprint.route("/self-stocks")
    @login_required
    def self_stocks():
        settings = get_settings()
        return render_template("self_stocks.html", ux_env_hints=_ux_env_hints(settings))

    @blueprint.route("/long-term-select")
    @login_required
    def long_term_select():
        settings = get_settings()
        return render_template("long_term_select.html", ux_env_hints=_ux_env_hints(settings))

    @blueprint.route("/stock-selector")
    @login_required
    def stock_selector():
        settings = get_settings()
        return render_template("stock_selector.html", ux_env_hints=_ux_env_hints(settings))

    @blueprint.route("/signal-flag")
    @login_required
    def signal_flag():
        settings = get_settings()
        return render_template(
            "signal_flag.html",
            enable_qlib=settings.enable_qlib,
            enable_celery=settings.enable_celery,
            ux_env_hints=_ux_env_hints(settings),
        )

    @blueprint.route("/signal-observations")
    @login_required
    def signal_observations():
        settings = get_settings()
        return render_template("signal_observations.html", ux_env_hints=_ux_env_hints(settings))

    @blueprint.route("/investment-managers")
    @login_required
    def investment_managers():
        settings = get_settings()
        return render_template("investment_managers.html", ux_env_hints=_ux_env_hints(settings))

    @blueprint.route("/investment-managers/<manager_id>")
    @login_required
    def investment_manager_detail(manager_id: str):
        settings = get_settings()
        return render_template("investment_manager_detail.html", manager_id=manager_id, ux_env_hints=_ux_env_hints(settings))

    @blueprint.route("/selection-result/<task_id>")
    @login_required
    def selection_result(task_id: str):
        settings = get_settings()
        return render_template("selection_result.html", task_id=task_id, ux_env_hints=_ux_env_hints(settings))

    @blueprint.route("/portfolio")
    @login_required
    def portfolio():
        settings = get_settings()
        return render_template("portfolio.html", ux_env_hints=_ux_env_hints(settings))

    @blueprint.route("/portfolio/<portfolio_id>")
    @login_required
    def portfolio_detail(portfolio_id: str):
        settings = get_settings()
        return render_template("portfolio_detail.html", portfolio_id=portfolio_id, ux_env_hints=_ux_env_hints(settings))

