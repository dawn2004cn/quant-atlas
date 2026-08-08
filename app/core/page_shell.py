"""Page shell helpers: per-route CSS preload hints for classic Flask UI."""

from __future__ import annotations

from typing import Final

# Flask endpoint name -> static CSS path (relative to static/)
_PAGE_CSS_PRELOAD: Final[dict[str, str]] = {
    "pages.daily_workbench": "css/pages/workbench.css",
    "pages.self_stocks": "css/pages/market.css",
    "pages.market_panorama": "css/pages/market.css",
    "pages.global_radar": "css/pages/market.css",
    "pages.hot_sectors": "css/pages/market.css",
    "pages.longhu_bang": "css/pages/market.css",
    "pages.yanbao_hub": "css/pages/market.css",
    "pages.tdx_blocks": "css/pages/market.css",
    "pages.stock_detail": "css/pages/stock-detail.css",
    "pages.backtest": "css/pages/strategy.css",
    "pages.optimize": "css/pages/strategy.css",
    "pages.attribution_dashboard": "css/pages/strategy.css",
    "pages.strategy_snapshots": "css/pages/strategy.css",
    "pages.professional_workbench": "css/pages/strategy.css",
    "pages.stock_selector": "css/pages/strategy.css",
    "pages.signal_flag": "css/pages/strategy.css",
    "pages.signal_observations": "css/pages/strategy.css",
    "pages.long_term_select": "css/pages/strategy.css",
    "pages.strategy_wizard": "css/pages/strategy-wizard.css",
    "pages.strategy_compare": "css/pages/strategy.css",
    "pages.factor_repository": "css/pages/factor.css",
    "pages.factor_detail": "css/pages/factor.css",
    "pages.factor_evolution": "css/pages/factor.css",
    "pages.quant_lab": "css/pages/research.css",
    "pages.research_pipeline": "css/pages/research.css",
    "pages.data_lake_health": "css/pages/data-lake.css",
    "pages.portfolio_resonance": "css/pages/zen-pages.css",
    "pages.decision_replay_space": "css/pages/research.css",
    "pages.research_canvas": "css/pages/research-canvas.css",
    "pages.strategy_compare": "css/pages/strategy.css",
    "pages.attribution_dashboard": "css/pages/strategy.css",
    "pages.ai_research_report": "css/pages/research.css",
    "pages.ai_investment_committee": "css/pages/research.css",
    "pages.ai_analysis": "css/pages/research.css",
    "pages.ai_research_report": "css/pages/research.css",
    "pages.ai_investment_committee": "css/pages/research.css",
    "pages.shadow_account": "css/pages/portfolio.css",
    "pages.portfolio": "css/pages/portfolio.css",
    "truth_droplet.truth_droplet_page": "css/pages/truth.css",
    "pages.alert_center": "css/pages/system.css",
    "pages.observability": "css/pages/system.css",
    "pages.retail_assistant": "css/pages/user.css",
    "pages.profile": "css/pages/user.css",
}


def page_css_preload_for_endpoint(endpoint: str | None) -> str | None:
    """Return static CSS path to preload for the current page, if known."""
    if not endpoint:
        return None
    return _PAGE_CSS_PRELOAD.get(endpoint)
