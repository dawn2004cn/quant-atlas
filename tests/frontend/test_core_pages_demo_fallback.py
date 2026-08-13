"""Core SPA pages must fall back to labeled demo rows when live lists are empty."""

from __future__ import annotations

from pathlib import Path

FE = Path(__file__).resolve().parents[2] / "frontend" / "src"


def test_demo_catalog_exports_core_lists() -> None:
    text = (FE / "lib" / "demoCatalog.ts").read_text(encoding="utf-8")
    for token in (
        "DEMO_STOCKS",
        "DEMO_SECTORS",
        "DEMO_PORTFOLIO",
        "DEMO_SELECTOR",
        "DEMO_PANORAMA_ROWS",
        "DEMO_GLOBAL_RADAR",
        "DEMO_LONGHU",
        "DEMO_TDX_BLOCKS",
        "DEMO_FACTORS",
        "DEMO_YANBAO",
        "DEMO_SIGNAL_FLAGS",
        "DEMO_WIZARD_TEMPLATES",
        "DEMO_STRATEGY_SNAPSHOTS",
        "DEMO_MLFLOW_RUNS",
        "DEMO_OBSERVATIONS",
        "DEMO_ALERTS",
        "DEMO_ZEN",
        "DEMO_SELECTION_RESULT",
        "DEMO_PORTFOLIO_DETAIL",
        "DEMO_LISTINGS",
        "DEMO_MANAGED_STOCKS",
        "DEMO_HEDGE_FUND",
        "DEMO_COMMITTEE_SELECTION",
        "DEMO_INVESTMENT_MANAGERS",
        "DEMO_EXPERT_TEAMS",
        "DEMO_MOMENTS",
        "DEMO_MESSAGES",
        "DEMO_WAR_ROOM",
        "DEMO_COMMITTEE_DASHBOARD",
        "DEMO_TASKS",
        "DEMO_SWARM_DASHBOARD",
        "DEMO_SWARM_DESIGNER",
        "DEMO_RESEARCH_PIPELINE",
        "DEMO_RESEARCH_CANVAS",
        "DEMO_AGENTS",
        "DEMO_CAPABILITIES",
        "DEMO_VOICE_BRIEFING",
        "DEMO_ALPHA_FACTORY",
        "DEMO_DECISION_REPLAYS",
        "DEMO_COLLABORATION",
        "DEMO_OBSERVABILITY",
        "DEMO_INVESTMENT_COMMITTEE",
        "DEMO_ARCHITECTURE_ROADMAP",
        "DEMO_RETAIL_ASSISTANT",
        "DEMO_PORTFOLIO_RESONANCE",
    ):
        assert token in text, token
    assert "600519" in text


def test_core_pages_use_demo_fallback() -> None:
    pages = (
        "SelfStocks.tsx",
        "HotSectors.tsx",
        "Portfolio.tsx",
        "StockSelector.tsx",
        "MarketPanorama.tsx",
        "GlobalRadar.tsx",
        "LonghuBang.tsx",
        "TdxBlocks.tsx",
        "FactorRepository.tsx",
        "YanbaoHub.tsx",
        "SignalFlag.tsx",
        "RunHistory.tsx",
        "StrategyWizard.tsx",
        "StrategySnapshots.tsx",
        "SignalObservations.tsx",
        "AlertCenter.tsx",
        "ZenDashboard.tsx",
        "SelectionResult.tsx",
        "PortfolioDetail.tsx",
        "Marketplace.tsx",
        "StocksManage.tsx",
        "AIHedgeFund.tsx",
        "AICommitteeSelection.tsx",
        "InvestmentManagers.tsx",
        "InvestmentManagerDetail.tsx",
        "ExpertTeams.tsx",
        "Moments.tsx",
        "MessageCenter.tsx",
        "WarRoom.tsx",
        "AICommitteeDashboard.tsx",
        "TaskCenter.tsx",
        "SwarmDashboard.tsx",
        "SwarmDesigner.tsx",
        "ResearchPipeline.tsx",
        "ResearchCanvas.tsx",
        "AgentCenter.tsx",
        "Capabilities.tsx",
        "VoiceBriefing.tsx",
        "AlphaFactory.tsx",
        "DecisionReplaySpace.tsx",
        "CollaborationWorkspace.tsx",
        "Observability.tsx",
        "AIInvestmentCommittee.tsx",
        "ArchitectureRoadmap.tsx",
        "RetailAssistant.tsx",
        "PortfolioResonance.tsx",
    )
    for name in pages:
        text = (FE / "pages" / name).read_text(encoding="utf-8")
        assert "DemoBanner" in text, name
        assert "demoCatalog" in text or "DEMO_" in text, name
        assert "window.location" not in text, name
    managers = (FE / "pages" / "InvestmentManagers.tsx").read_text(encoding="utf-8")
    assert "/app/investment-managers" not in managers
    assert "/investment-managers/" in managers
