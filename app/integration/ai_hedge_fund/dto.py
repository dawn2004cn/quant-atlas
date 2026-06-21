from __future__ import annotations
"""DTOs for AI Hedge Fund integration."""


from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class AgentSignal:
    """Signal from a single analyst agent."""
    agent_name: str
    agent_style: str
    signal: str
    confidence: int
    reasoning: str
    analysis_details: dict[str, Any] = field(default_factory=dict)


@dataclass
class HedgeFundAnalysisRequest:
    """Request for AI Hedge Fund analysis."""
    symbols: list[str]
    start_date: str
    end_date: str
    selected_agents: list[str] | None = None
    portfolio_value: float = 1000000.0


@dataclass
class AnalystOpinion:
    """Opinion from an analyst (mirrors InvestmentCommittee's AgentOpinion)."""
    agent_name: str
    conclusion: str
    confidence: float
    reasoning: str
    data_sources: list[str] = field(default_factory=list)


@dataclass
class ValidationResult:
    """Result from RD-Agent/Qlib validation."""
    validation_type: str
    passed: bool
    metrics: dict[str, Any] = field(default_factory=dict)
    backtest_result: dict[str, Any] | None = None
    errors: list[str] = field(default_factory=list)


@dataclass
class HedgeFundAnalysisResult:
    """Complete analysis result with validation."""
    symbols: list[str]
    analysis_timestamp: datetime = field(default_factory=datetime.now)

    agent_signals: list[AgentSignal] = field(default_factory=list)
    aggregated_signal: str = ""
    consensus_score: float = 0.0

    validation_results: list[ValidationResult] = field(default_factory=list)
    validation_passed: bool = False

    rd_agent_job_id: str | None = None
    qlib_backtest_result: dict[str, Any] | None = None

    summary: str = ""
    is_ready_for_trading: bool = False


@dataclass
class ResearchReport:
    """Final research report combining AI analysis and validation."""
    report_id: str
    symbol: str
    generated_at: datetime

    ai_analysis: HedgeFundAnalysisResult
    validation: ValidationResult

    final_recommendation: str
    risk_assessment: str
    confidence_score: float

    sources: list[str] = field(default_factory=list)