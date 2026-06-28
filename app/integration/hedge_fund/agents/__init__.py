from __future__ import annotations

"""AI Hedge Fund Agents - 18 Master Traders.

This module integrates all 18 agents from ai-hedge-fund project:
- 12 Legendary Investors: Warren Buffett, Charlie Munger, Ben Graham, Bill Ackman, Cathie Wood,
  Michael Burry, Peter Lynch, Phil Fisher, Stanley Druckenmiller, Mohnish Pabrai, Nassim Taleb, Aswath Damodaran
- 6 Professional Analysts: Valuation, Fundamentals, Technicals, Sentiment, Risk Manager, Portfolio Manager

Each agent analyzes stocks using their signature investment philosophy.

Plus Openclaw personality enhancements from agent/workspaces-*.
"""


import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any

from app.core.logger import get_logger

logger = get_logger(__name__)


class HedgeFundAgentId(str, Enum):
    WARREN_BUFFETT = "warren_buffett"
    CHARLIE_MUNGER = "charlie_munger"
    BEN_GRAHAM = "ben_graham"
    BILL_ACKMAN = "bill_ackman"
    CATHIE_WOOD = "cathie_wood"
    MICHAEL_BURRY = "michael_burry"
    PETER_LYNCH = "peter_lynch"
    PHIL_FISHER = "phil_fisher"
    STANLEY_DRUCKENMILLER = "stanley_druckenmiller"
    MOHNISH_PABRAI = "mohnish_pabrai"
    NASSIM_TALEB = "nassim_taleb"
    ASWATH_DAMODARAN = "aswath_damodaran"
    VALUATION = "valuation"
    FUNDAMENTALS = "fundamentals"
    TECHNICALS = "technicals"
    SENTIMENT = "sentiment"
    RISK_MANAGER = "risk_manager"
    PORTFOLIO_MANAGER = "portfolio_manager"


AGENT_METADATA = {
    "warren_buffett": {
        "name": "Warren Buffett",
        "title": "Oracle of Omaha",
        "style": "Value Investing",
        "description": "Seeks wide economic moats, financial fortress, and intrinsic value.",
    },
    "charlie_munger": {
        "name": "Charlie Munger",
        "title": "Vice Chairman",
        "style": "Business Quality",
        "description": "Focuses on excellent businesses at fair prices, strong management.",
    },
    "ben_graham": {
        "name": "Ben Graham",
        "title": "Father of Value Investing",
        "style": "Deep Value",
        "description": "Graham's Net-Net strategy, margin of safety, intrinsic value.",
    },
    "bill_ackman": {
        "name": "Bill Ackman",
        "title": "Activist Investor",
        "style": "Activist Investing",
        "description": "High-conviction bets, brand moats, FCF, activism potential.",
    },
    "cathie_wood": {
        "name": "Cathie Wood",
        "title": "ARK Queen",
        "style": "Innovation/Growth",
        "description": "Disruptive innovation, exponential tech, big ideas.",
    },
    "michael_burry": {
        "name": "Michael Burry",
        "title": "The Big Short",
        "style": "Contrarian/Deep Value",
        "description": "Contrarian deep value, hidden assets, restructuring opportunities.",
    },
    "peter_lynch": {
        "name": "Peter Lynch",
        "title": "Legendary Fund Manager",
        "style": "Growth Investing",
        "description": "Invest what you know, 10-baggers, lifestyle investing.",
    },
    "phil_fisher": {
        "name": "Phil Fisher",
        "title": "Growth Stock Pioneer",
        "style": "Growth Stocks",
        "description": "Scuttlebutt method, 15 points, growth at reasonable price.",
    },
    "stanley_druckenmiller": {
        "name": "Stanley Druckenmiller",
        "title": "Macro Legend",
        "style": "Macro/Momentum",
        "description": "Asymmetric risk-reward, macro, momentum, big bets.",
    },
    "mohnish_pabrai": {
        "name": "Mohnish Pabrai",
        "title": "Dhandho Investor",
        "style": "GARP",
        "description": "Dhandho investing, low-risk high-reward, clones.",
    },
    "nassim_taleb": {
        "name": "Nassim Taleb",
        "title": "AntiFragility Author",
        "style": "Risk/Antifragility",
        "description": "Tail risk, convexity, antifragility, black swan hedging.",
    },
    "aswath_damodaran": {
        "name": "Aswath Damodaran",
        "title": "Valuation Guru",
        "style": "Valuation",
        "description": "DCF, multiples, rigorous financial modeling.",
    },
    "valuation": {
        "name": "Valuation Agent",
        "title": "Quantitative Valuation",
        "style": "Valuation",
        "description": "Calculates intrinsic value, generates valuation signals.",
    },
    "fundamentals": {
        "name": "Fundamentals Agent",
        "title": "Financial Analyst",
        "style": "Fundamentals",
        "description": "Financial metrics, ROE, growth, profitability signals.",
    },
    "technicals": {
        "name": "Technicals Agent",
        "title": "Technical Analyst",
        "style": "Technical Analysis",
        "description": "Price action, momentum, chart patterns.",
    },
    "sentiment": {
        "name": "Sentiment Agent",
        "title": "Market Sentiment",
        "style": "Sentiment Analysis",
        "description": "News flow, social sentiment, crowd behavior.",
    },
    "risk_manager": {
        "name": "Risk Manager",
        "title": "Risk Officer",
        "style": "Risk Management",
        "description": "Volatility, drawdown, position sizing, risk limits.",
    },
    "portfolio_manager": {
        "name": "Portfolio Manager",
        "title": "Portfolio Strategist",
        "style": "Portfolio Construction",
        "description": "Signal aggregation, allocation, final decisions.",
    },
}


def get_agent_metadata(agent_id: str) -> dict[str, Any]:
    """Get metadata for an agent."""
    return AGENT_METADATA.get(agent_id, {})


def list_all_agents() -> list[dict[str, Any]]:
    """List all available agents."""
    return [
        {"id": agent_id, **metadata}
        for agent_id, metadata in AGENT_METADATA.items()
    ]


__all__ = [
    "HedgeFundAgentId",
    "AGENT_METADATA",
    "get_agent_metadata",
    "list_all_agents",
    "get_openclaw_personalities",
    "get_enhanced_system_prompt",
    "get_communication_style",
]

# Lazy imports for Openclaw integration
from .openclaw import get_communication_style, get_enhanced_system_prompt, get_openclaw_personalities
