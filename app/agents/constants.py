from __future__ import annotations

"""Agent Constants - Centralized management of agent names, keys, and roles.

This module consolidates all magic strings used across the agent system.
Prevents refactoring errors and improves maintainability.

Usage:
    from app.agents.constants import AgentName, BlackboardKey, DepartmentName
"""


from enum import Enum


class AgentName(Enum):
    """Unique agent identifiers."""
    SUPERVISOR = "Supervisor"
    MACRO_ANALYST = "MacroAnalyst"
    FUNDAMENTAL_ANALYST = "FundamentalAnalyst"
    TECHNICAL_ANALYST = "TechnicalAnalyst"
    SENTIMENT_ANALYST = "SentimentAnalyst"
    BACKTEST_ANALYST = "BacktestAnalyst"
    RISK_MANAGER = "RiskManager"
    SYNTHESIS_SERVICE = "SynthesisService"


class DepartmentName(Enum):
    """Department names for hierarchical teams."""
    MACRO_DEPARTMENT = "MacroDepartment"
    FUNDAMENTAL_DEPARTMENT = "FundamentalDepartment"
    TECHNICAL_DEPARTMENT = "TechnicalDepartment"
    SENTIMENT_DEPARTMENT = "SentimentDepartment"
    BACKTEST_DEPARTMENT = "BacktestDepartment"
    RISK_DEPARTMENT = "RiskDepartment"


class BlackboardKey(Enum):
    """Evidence blackboard keys."""
    OHLCV = "ohlcv"
    FUNDAMENTALS = "fundamentals"
    PRICE_HISTORY = "price_history"
    NEWS_SENTIMENT = "news_sentiment"
    BACKTEST_RESULT = "backtest_result"
    RISK_ASSESSMENT = "risk_assessment"
    CRITICAL_RISK = "critical_risk"
    DELISTING_RISK = "delisting_risk"
    FRAUD_INDICATOR = "fraud_indicator"


class NodeName(Enum):
    """LangGraph node names."""
    SUPERVISOR = "supervisor_node"
    MACRO = "macro_analyst_node"
    FUNDAMENTAL = "fundamental_analyst_node"
    TECHNICAL = "technical_analyst_node"
    SENTIMENT = "sentiment_analyst_node"
    BACKTEST = "backtest_analyst_node"
    RISK = "risk_manager_node"
    EVIDENCE_ROUTING = "evidence_routing_node"
    SYNTHESIS = "synthesis_node"
    DEPARTMENT_PARALLEL = "department_parallel_node"


class EvidenceKey(Enum):
    """Evidence keys for structured communication."""
    PRICE_DATA = "price_data"
    FINANCIAL_DATA = "financial_data"
    TECHNICAL_PATTERN = "technical_pattern"
    SENTIMENT_SCORE = "sentiment_score"
    BACKTEST_METRICS = "backtest_metrics"
    RISK_SIGNAL = "risk_signal"
    MARKET_REGIME = "market_regime"


class LLMTierConfig(Enum):
    """LLM tier configurations."""
    L1_FAST = "gpt-4o-mini"
    L2_REASONING = "gpt-4o"
    CLAUDE_REASONING = "claude-3.5-sonnet"


AGENT_DEPARTMENT_MAP = {
    AgentName.MACRO_ANALYST: DepartmentName.MACRO_DEPARTMENT,
    AgentName.FUNDAMENTAL_ANALYST: DepartmentName.FUNDAMENTAL_DEPARTMENT,
    AgentName.TECHNICAL_ANALYST: DepartmentName.TECHNICAL_DEPARTMENT,
    AgentName.SENTIMENT_ANALYST: DepartmentName.SENTIMENT_DEPARTMENT,
    AgentName.BACKTEST_ANALYST: DepartmentName.BACKTEST_DEPARTMENT,
    AgentName.RISK_MANAGER: DepartmentName.RISK_DEPARTMENT,
}

DEPARTMENT_AGENTS_MAP = {
    DepartmentName.MACRO_DEPARTMENT: [AgentName.MACRO_ANALYST],
    DepartmentName.FUNDAMENTAL_DEPARTMENT: [AgentName.FUNDAMENTAL_ANALYST],
    DepartmentName.TECHNICAL_DEPARTMENT: [AgentName.TECHNICAL_ANALYST],
    DepartmentName.SENTIMENT_DEPARTMENT: [AgentName.SENTIMENT_ANALYST],
    DepartmentName.BACKTEST_DEPARTMENT: [AgentName.BACKTEST_ANALYST],
    DepartmentName.RISK_DEPARTMENT: [AgentName.RISK_MANAGER],
}

CRITICAL_RISK_KEYS = [
    BlackboardKey.DELISTING_RISK.value,
    BlackboardKey.FRAUD_INDICATOR.value,
    BlackboardKey.CRITICAL_RISK.value,
]

TOOL_CONTEXT_LIMITS = {
    "macro_report": 4000,
    "fundamental_report": 3000,
    "technical_report": 2500,
    "sentiment_report": 2000,
    "backtest_report": 2000,
    "risk_report": 1500,
}


def get_agent_name_str(agent: AgentName) -> str:
    """Get string representation of agent name."""
    return agent.value


def get_department_name_str(dept: DepartmentName) -> str:
    """Get string representation of department name."""
    return dept.value


def get_llm_tier_for_agent(agent: AgentName) -> LLMTierConfig:
    """Get recommended LLM tier for specific agent."""
    tier_map = {
        AgentName.MACRO_ANALYST: LLMTierConfig.L1_FAST,
        AgentName.SENTIMENT_ANALYST: LLMTierConfig.L1_FAST,
        AgentName.FUNDAMENTAL_ANALYST: LLMTierConfig.L2_REASONING,
        AgentName.TECHNICAL_ANALYST: LLMTierConfig.L2_REASONING,
        AgentName.BACKTEST_ANALYST: LLMTierConfig.L2_REASONING,
        AgentName.RISK_MANAGER: LLMTierConfig.L2_REASONING,
        AgentName.SUPERVISOR: LLMTierConfig.L2_REASONING,
    }
    return tier_map.get(agent, LLMTierConfig.L2_REASONING)
