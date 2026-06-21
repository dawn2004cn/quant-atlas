"""User Journey definitions and route mappings.

Maps existing route modules to user-facing journeys without modifying
any existing route files. Provides a /journey/* namespace that groups
endpoints by user intent.

Journeys:
  discovery  — 发现 (market overview, stock search, hot sectors)
  research   — 研究 (AI analysis, factors, strategies, reports)
  execution  — 执行 (trading, portfolio, risk, signals)
  review     — 复盘 (attribution, snapshots, replay, moments)
  monitor    — 监控 (health, alerts, tasks, data infrastructure)
  manage     — 管理 (user profile, lifecycle, watchlist, collaboration)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class JourneyDefinition:
    """Describes a user-facing journey."""

    name: str
    label: str
    description: str
    icon: str
    route_modules: list[str] = field(default_factory=list)
    url_prefix: str = ""


# Route module → journey mapping
# Each entry lists which route class names (from @register_routes) belong to the journey.
JOURNEY_ROUTE_MAP: dict[str, list[str]] = {
    "discovery": [
        "market_core",
        "stock",
        "hot_sectors",
        "market_aux",
        "global_market",
        "market_sentiment",
        "pytdx",
        "diagnosis",
        "industry_chain",
        "nl",
        "smart_briefing",
        "chart_vision",
    ],
    "research": [
        "ai_hedge_fund",
        "fingpt",
        "factor",
        "strategy_copilot",
        "strategy_optimization",
        "strategy_shadow",
        "evidence_graph",
        "investment_committee",
        "qlib_rd",
        "quant_ai",
        "ai_committee_selection",
        "research_reports",
        "integration_stack",
        "manifest_10",
        "hyper_simulator",
        "data_truth",
        "swarm_topology",
        "workflows",
    ],
    "execution": [
        "trading",
        "portfolio",
        "portfolio_users",
        "execution",
        "trade_plan",
        "signal_flag",
        "signal_observations",
        "trading_preflight",
        "risk",
        "simulation",
        "self_healing_execution",
        "ten_kings",
        "recommendations",
        "arbiter",
        "data_optimizer",
    ],
    "review": [
        "attribution",
        "strategy_snapshots",
        "decision_replay",
        "decision_provenance",
        "decision_theater",
        "investment_managers",
        "moments",
        "reviews",
        "challenges",
        "reviews_tracking",
    ],
    "monitor": [
        "alert_center",
        "health",
        "system_health",
        "monitoring",
        "memory",
        "task_ops",
        "task_pipeline",
        "data_infrastructure",
    ],
    "manage": [
        "user_lifecycle",
        "user_profile",
        "user_system",
        "collaboration",
        "watchlist_agent",
        "watchlist_experience",
        "mesh",
        "admin_stocks",
        "system",
        "experiments",
    ],
}


JOURNEY_METADATA: dict[str, dict[str, Any]] = {
    "discovery": {
        "label": "发现",
        "label_en": "Discovery",
        "description": "市场全景、行情、热点、自选股",
        "icon": "compass",
    },
    "research": {
        "label": "研究",
        "label_en": "Research",
        "description": "AI 分析、因子、策略、研报",
        "icon": "microscope",
    },
    "execution": {
        "label": "执行",
        "label_en": "Execution",
        "description": "交易、组合、风控、信号",
        "icon": "play-circle",
    },
    "review": {
        "label": "复盘",
        "label_en": "Review",
        "description": "归因、快照、回放、动态",
        "icon": "history",
    },
    "monitor": {
        "label": "监控",
        "label_en": "Monitor",
        "description": "健康、告警、任务、数据",
        "icon": "activity",
    },
    "manage": {
        "label": "管理",
        "label_en": "Manage",
        "description": "用户、协作、配置",
        "icon": "settings",
    },
}


def get_journey_names() -> list[str]:
    """Return ordered list of all journey names."""
    return list(JOURNEY_METADATA.keys())


def get_route_modules_for_journey(journey_name: str) -> list[str]:
    """Return route module names that belong to a journey."""
    return JOURNEY_ROUTE_MAP.get(journey_name, [])


def get_journey_for_route_module(route_name: str) -> str | None:
    """Return the journey name that a route module belongs to, or None."""
    for journey, modules in JOURNEY_ROUTE_MAP.items():
        if route_name in modules:
            return journey
    return None


def get_journey_metadata(journey_name: str) -> dict[str, Any] | None:
    """Return metadata dict for a journey, or None."""
    return JOURNEY_METADATA.get(journey_name)


def build_journey_context() -> dict[str, Any]:
    """Build full journey catalog for API responses."""
    journeys = []
    for name in get_journey_names():
        meta = JOURNEY_METADATA[name]
        journeys.append(
            {
                "name": name,
                "label": meta["label"],
                "label_en": meta["label_en"],
                "description": meta["description"],
                "icon": meta["icon"],
                "route_count": len(JOURNEY_ROUTE_MAP.get(name, [])),
            }
        )
    return {"schema_version": "v1", "journeys": journeys}


__all__ = [
    "JourneyDefinition",
    "JOURNEY_ROUTE_MAP",
    "JOURNEY_METADATA",
    "get_journey_names",
    "get_route_modules_for_journey",
    "get_journey_for_route_module",
    "get_journey_metadata",
    "build_journey_context",
]
