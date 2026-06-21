"""Page routes: ai domain. Split from pages.py."""

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
from app.presentation.strategic_sunset_hooks import require_strategic_feature

def register_pages(blueprint: Blueprint) -> None:
    @blueprint.route("/ai-hedge-fund")
    @login_required
    def ai_hedge_fund():
        return render_template("ai_hedge_fund.html")

    @blueprint.route("/alpha-factory")
    @login_required
    def alpha_factory():
        settings = get_settings()
        return render_template(
            "alpha_factory.html",
            enable_qlib=settings.enable_qlib,
            enable_rd_agent=settings.enable_rd_agent,
        )

    @blueprint.route("/factor-evolution")
    @login_required
    def factor_evolution():
        return render_template("factor_evolution.html")

    @blueprint.route("/ai-committee")
    @login_required
    def ai_investment_committee():
        return render_template("ai_investment_committee.html")

    @blueprint.route("/ai-committee-dashboard")
    @login_required
    def ai_committee_dashboard():
        return render_template("ai_committee_dashboard.html")

    @blueprint.route("/ai-committee-selection")
    @login_required
    def ai_committee_selection():
        return render_template("ai_committee_selection.html")

    @blueprint.route("/nl-strategy")
    @login_required
    def nl_strategy():
        return render_template("nl_strategy.html")

    @blueprint.route("/ai-analysis")
    @login_required
    def ai_analysis():
        return render_template("ai_analysis.html")

    @blueprint.route("/ai-research-report")
    @login_required
    def ai_research_report():
        return render_template("ai_research_report.html")

    @blueprint.route("/ai-chat")
    @login_required
    def ai_chat():
        return render_template("ai_chat.html")

    @blueprint.route("/research-pipeline")
    @login_required
    def research_pipeline():
        return render_template("research_pipeline.html")

    @blueprint.route("/factor-repository")
    @login_required
    def factor_repository():
        return render_template("factor_repository.html")

    @blueprint.route("/factor/<factor_id>")
    @login_required
    def factor_detail(factor_id: str):
        return render_template("factor_detail.html", factor_id=factor_id)

    @blueprint.route("/alpha-marketplace")
    @login_required
    @require_strategic_feature("alpha_marketplace")
    def alpha_marketplace():
        return render_template("marketplace.html")

    @blueprint.route("/user-tiers/retail")
    @login_required
    def user_tiers_retail():
        from flask import redirect
        return redirect("/retail-assistant", code=302)

    @blueprint.route("/user-tiers/boutique")
    @login_required
    def user_tiers_boutique():
        return render_template("user_tiers_boutique.html")

    @blueprint.route("/user-tiers/investment")
    @login_required
    def user_tiers_investment():
        return render_template("user_tiers_investment.html")

    @blueprint.route("/user-tiers/fund")
    @login_required
    def user_tiers_fund():
        return render_template("user_tiers_fund.html")

    @blueprint.route("/user-tiers/institution")
    @login_required
    def user_tiers_institution():
        return render_template("user_tiers_institution.html")

    @blueprint.route("/strategy-wizard")
    @login_required
    def strategy_wizard():
        return render_template("strategy_wizard.html")

    @blueprint.route("/data-lake-health")
    @login_required
    def data_lake_health():
        return render_template("data_lake_health.html")

    @blueprint.route("/professional-workbench")
    @login_required
    def professional_workbench():
        return render_template("professional_workbench.html")

    @blueprint.route("/user-spectrum-hub")
    @login_required
    def user_spectrum_hub():
        return render_template("user_spectrum_hub.html")

    @blueprint.route("/zen-terminal")
    @login_required
    def zen_terminal():
        return render_template("zen_terminal.html")

    @blueprint.route("/portfolio-resonance")
    @login_required
    def portfolio_resonance():
        return render_template("portfolio_resonance.html")

    @blueprint.route("/zen-dashboard")
    @login_required
    def zen_dashboard():
        return render_template("zen_dashboard.html")


