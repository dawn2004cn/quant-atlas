"""Navigation menu visibility — hide off-topic items from nav while keeping routes.

Inspired by focused menus in DeltaFStation, OpenTrading, and ashare-ai-analyst:
core flows = market/workbench → research → strategy → account.

Set ``NAV_SHOW_EXPERIMENTAL=1`` to reveal all experimental / meta entries, or
``NAV_SHOW_<ITEM_ID>=1`` for individual items (uppercase, e.g. ``NAV_SHOW_MOMENTS=1``).
"""

from __future__ import annotations

from app.core.runtime_config import get_runtime_bool

# item_id → human label (for docs / retired hints)
_NAV_ITEMS: dict[str, str] = {
    # Workbench — secondary / global views
    "global_radar": "全球透视塔",
    "spa_shell": "SPA 版",
    # Research — experimental / showcase AI surfaces
    "ai_investment_committee": "AI 投委会",
    "ai_hedge_fund": "分析师天团",
    "agent_center": "Agent 中心",
    "voice_briefing": "语音简报",
    "research_canvas": "Research Canvas",
    # Strategy — advanced / ops
    "alpha_factory": "Alpha Factory",
    "data_lake_health": "数据湖健康",
    # Mine — social / role demos / platform meta
    "user_tiers": "角色工作台",
    "zen_terminal": "禅意终端",
    "integration_hub": "集成中枢",
    "observability": "观测台",
    "moments": "研究朋友圈",
    "collaboration_workspace": "协作空间",
    "investment_managers": "投资经理",
}

# Hidden from nav by default; routes and code remain.
_NAV_HIDDEN_DEFAULT: frozenset[str] = frozenset(
    {
        "spa_shell",
        "ai_hedge_fund",
        "agent_center",
        "voice_briefing",
        "research_canvas",
        "alpha_factory",
        "data_lake_health",
        "user_tiers",
        "zen_terminal",
        "integration_hub",
        "observability",
        "moments",
        "collaboration_workspace",
        "investment_managers",
    }
)


def _env_key(item_id: str) -> str:
    return f"NAV_SHOW_{item_id.upper()}"


def nav_visible(item_id: str) -> bool:
    """Return True when a nav item should appear in menus."""
    if item_id not in _NAV_ITEMS:
        return True
    if get_runtime_bool("NAV_SHOW_EXPERIMENTAL", False):
        return True
    if get_runtime_bool(_env_key(item_id), False):
        return True
    return item_id not in _NAV_HIDDEN_DEFAULT


def jinja_nav_flags() -> dict[str, bool]:
    """Template context: ``nav_global_radar``, etc."""
    return {f"nav_{name}": nav_visible(name) for name in _NAV_ITEMS}


def api_nav_flags() -> dict[str, bool]:
    """SPA / API payload — ``nav_show_<item_id>`` keys."""
    return {f"nav_show_{name}": nav_visible(name) for name in _NAV_ITEMS}


def nav_item_label(item_id: str) -> str:
    return _NAV_ITEMS.get(item_id, item_id)
