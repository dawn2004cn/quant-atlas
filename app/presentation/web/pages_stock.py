"""Page routes: stock domain. Split from pages.py."""

from __future__ import annotations

from flask import (
    Blueprint,
    Response,
    abort,
    make_response,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_required
from werkzeug.utils import safe_join

from app.modules.system.services.integration.integration_hub_service import (
    build_integration_hub_context,
)
from app.config import BASE_DIR, get_settings
from app.models import STRATEGY_REGISTRY_GROUPS
from app.presentation.web.page_shell import render_page_shell, ux_env_hints as _ux_env_hints

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
        return redirect("/app/strategy-compare", code=302)

    @blueprint.route("/attribution-dashboard")
    @login_required
    def attribution_dashboard():
        return render_template("attribution_dashboard.html")

    @blueprint.route("/strategy-snapshots")
    @login_required
    def strategy_snapshots():
        return redirect("/app/strategy-snapshots", code=302)

    @blueprint.route("/decision-snapshot/<snapshot_id>")
    @login_required
    def decision_snapshot(snapshot_id: str):
        return redirect(f"/app/decision-snapshot/{snapshot_id}", code=302)

    @blueprint.route("/share/decision/<share_token>")
    def decision_snapshot_public(share_token: str):
        return redirect(f"/app/share/decision/{share_token}", code=302)

    @blueprint.route("/self-stocks")
    @login_required
    def self_stocks():
        return redirect("/app/self-stocks", code=302)

    @blueprint.route("/long-term-select")
    @login_required
    def long_term_select():
        return redirect("/app/long-term-select", code=302)

    @blueprint.route("/stock-selector")
    @login_required
    def stock_selector():
        return redirect("/app/stock-selector", code=302)

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
        return redirect("/app/signal-observations", code=302)

    @blueprint.route("/investment-managers")
    @login_required
    def investment_managers():
        return redirect("/app/investment-managers", code=302)

    @blueprint.route("/investment-managers/<manager_id>")
    @login_required
    def investment_manager_detail(manager_id: str):
        return redirect(f"/app/investment-managers/{manager_id}", code=302)

    @blueprint.route("/selection-result/<task_id>")
    @login_required
    def selection_result(task_id: str):
        return redirect(f"/app/selection-result/{task_id}", code=302)

    @blueprint.route("/portfolio")
    @login_required
    def portfolio():
        return redirect("/app/portfolio", code=302)

    @blueprint.route("/portfolio/<portfolio_id>")
    @login_required
    def portfolio_detail(portfolio_id: str):
        return redirect(f"/app/portfolio/{portfolio_id}", code=302)

