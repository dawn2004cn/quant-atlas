from __future__ import annotations

"""Unified Agent Registry - Combining quant-atlas + Openclaw agents.

This module merges:
1. quant-atlas hedge fund agents (18 legendary investors + analysts)
2. Openclaw workspace agents (specific personas with SOUL.md)

The result is a powerful unified agent system where:
- System agents get enhanced with Openclaw personalities
- Each agent has a unique identity, communication style, and investment philosophy
"""


from pathlib import Path
from typing import Any

AGENT_ROOT = Path("E:/project/workspace/myrepo/quant-atlas/agent")


OPENCLAW_WORKSPACES = {
    "buffett": "workspaces-stock-buffett",
    "munger": "workspaces-stock-munger",
    "lynch": "workspaces-stock-lynch",
    "simons": "workspaces-stock-simons",
    "soros": "workspaces-stock-soros",
    "xukaidong": "workspaces-stock-xukaidong",
    "geweidong": "workspaces-stock-geweidong",
    "xiaoqun": "workspaces-stock-xiaoqun",
    "mengzhu": "workspaces-stock-mengzhu",
}


def load_soul_md(workspace: str) -> str:
    """Load SOUL.md content from Openclaw workspace."""
    path = AGENT_ROOT / workspace / "SOUL.md"
    if path.exists():
        return path.read_text(encoding="utf-8")
    return ""


def load_agents_md(workspace: str) -> str:
    """Load AGENTS.md content from Openclaw workspace."""
    path = AGENT_ROOT / workspace / "AGENTS.md"
    if path.exists():
        return path.read_text(encoding="utf-8")
    return ""


def load_identity_md(workspace: str) -> str:
    """Load IDENTITY.md content from Openclaw workspace."""
    path = AGENT_ROOT / workspace / "IDENTITY.md"
    if path.exists():
        return path.read_text(encoding="utf-8")
    return ""


def get_openclaw_personalities() -> dict[str, dict[str, str]]:
    """Load all Openclaw workspace personalities."""
    personalities = {}

    for short_name, workspace in OPENCLAW_WORKSPACES.items():
        souls = load_soul_md(workspace)
        agents = load_agents_md(workspace)
        identity = load_identity_md(workspace)

        if souls:
            personalities[short_name] = {
                "workspace": workspace,
                "soul": souls,
                "agents": agents,
                "identity": identity,
            }

    return personalities


OPENCLAW_PERSONALITIES = None


def get_personality(agent_id: str) -> dict[str, str] | None:
    """Get personality data for an agent."""
    global OPENCLAW_PERSONALITIES
    if OPENCLAW_PERSONALITIES is None:
        OPENCLAW_PERSONALITIES = get_openclaw_personalities()

    return OPENCLAW_PERSONALITIES.get(agent_id)


AGENT_MAPPING = {
    "warren_buffett": "buffett",
    "charlie_munger": "munger",
    "peter_lynch": "lynch",
    "stanley_druckenmiller": "simons",
    "george_soros": "soros",
    "bill_ackman": "xukaidong",
    "cathie_wood": "xiaoqun",
    "michael_burry": "mengzhu",
}


def get_enhanced_system_prompt(agent_id: str, base_prompt: str) -> str:
    """Get enhanced system prompt by combining base with Openclaw personality.

    Args:
        agent_id: System agent ID (e.g., 'warren_buffett')
        base_prompt: Base system prompt from hedge_fund agents

    Returns:
        Enhanced prompt combining base + Openclaw SOUL.md personality
    """
    openclaw_id = AGENT_MAPPING.get(agent_id)
    if not openclaw_id:
        return base_prompt

    personality = get_personality(openclaw_id)
    if not personality:
        return base_prompt

    soul = personality.get("soul", "")
    agents_md = personality.get("agents", "")

    if not soul:
        return base_prompt

    enhanced = f"""{base_prompt}

---

## Your Enhanced Identity (from Openclaw)

{soul}

---

## Additional Guidelines

{agents_md}

---

Use your enhanced identity to communicate with unique style and personality."""

    return enhanced


def get_communication_style(agent_id: str) -> dict[str, Any]:
    """Get communication style for an agent.

    Returns dict with:
    - tone: 'calm', 'enthusiastic', 'caustic', 'cold', 'academic'
    - style: 'value', 'growth', 'quantitative', 'macro', 'technical'
    - typical_phrases: list of typical phrases this agent uses
    - emoji: representative emoji
    """
    openclaw_id = AGENT_MAPPING.get(agent_id)
    if not openclaw_id:
        return {"style": "default", "tone": "neutral", "typical_phrases": [], "emoji": "📊"}

    styles = {
        "buffett": {
            "tone": "calm_wisdom",
            "style": "value",
            "typical_phrases": [
                "价格是你付出的，价值是你得到的。",
                "护城河在，复利就在。",
                "别人恐惧时贪婪，别人贪婪时恐惧。",
                "慢慢来……复利会帮我们。",
            ],
            "emoji": "🦞🍒",
        },
        "munger": {
            "tone": "caustic_wisdom",
            "style": "quality",
            "typical_phrases": [
                "颠倒过来想。",
                "这生意太蠢，我不碰。",
                "理性是最好的风控。",
            ],
            "emoji": "🧐",
        },
        "lynch": {
            "tone": "enthusiastic",
            "style": "growth",
            "typical_phrases": [
                "买你看好的公司！",
                "10倍股就在生活里！",
                "数据说话，别猜。",
            ],
            "emoji": "📈",
        },
        "simons": {
            "tone": "cold_academic",
            "style": "quantitative",
            "typical_phrases": [
                "p<0.01，进。",
                "噪声主导，pass。",
                "信号显著，进场。",
            ],
            "emoji": "🧮📊",
        },
        "soros": {
            "tone": "adaptive",
            "style": "macro",
            "typical_phrases": [
                "趋势是你的朋友。",
                "错了就砍，反手。",
                "不确定性是我们的朋友。",
            ],
            "emoji": "🌍",
        },
    }

    return styles.get(openclaw_id, {"tone": "neutral", "style": "default", "typical_phrases": [], "emoji": "📊"})


__all__ = [
    "OPENCLAW_WORKSPACES",
    "get_personality",
    "get_enhanced_system_prompt",
    "get_communication_style",
    "AGENT_MAPPING",
    "get_openclaw_personalities",
]
