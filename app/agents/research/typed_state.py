from __future__ import annotations
"""Typed Research State - Pydantic-based state for LangGraph.

This module implements the LangGraph & DTO Integration from midify_plan10.md:
- TypedResearchState: Pydantic model replacing dict[str, Any]
- AgentReportDTO: Standardized report format
- Integration with AgentResponseDTO

This eliminates hardcoded string keys and provides type safety.
"""


from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class AgentReportDTO(BaseModel):
    """Standardized agent report format.

    Replaces the previous string-based report fields with structured data.
    """
    agent_name: str
    conclusion: str
    confidence: float
    key_evidence: dict[str, Any] = Field(default_factory=dict)
    narrative: str = ""
    timestamp: datetime = Field(default_factory=datetime.now)
    metadata: dict[str, Any] = Field(default_factory=dict)

    def to_summary(self) -> str:
        """Convert to short summary for display."""
        return f"[{self.agent_name}] {self.conclusion} ({self.confidence:.0%})"


class TypedResearchState(BaseModel):
    """Typed ResearchState for LangGraph.

    Replaces the previous dict[str, Any] with Pydantic models.
    Provides type safety and eliminates hardcoded string keys.
    """

    ticker: str = ""
    query: str = ""
    user_id: int = 0

    conversation_log: list[str] = Field(default_factory=list)

    macro_report: AgentReportDTO | None = None
    fundamental_report: AgentReportDTO | None = None
    technical_report: AgentReportDTO | None = None
    sentiment_report: AgentReportDTO | None = None
    backtest_report: AgentReportDTO | None = None

    risk_manager_report: AgentReportDTO | None = None
    decision_dashboard: str = ""

    debate_turn: int = 0
    investment_debate_bull: str = ""
    investment_debate_bear: str = ""
    investment_debate_history: str = ""

    risk_debate_turn: int = 0
    risk_debate_risky: str = ""
    risk_debate_safe: str = ""
    risk_debate_history: str = ""

    fingpt_forecast: dict[str, Any] = Field(default_factory=dict)

    supervisor_memo: str = ""

    def get_report(self, agent_name: str) -> AgentReportDTO | None:
        """Get report by agent name."""
        report_map = {
            "macro": self.macro_report,
            "fundamental": self.fundamental_report,
            "technical": self.technical_report,
            "sentiment": self.sentiment_report,
            "backtest": self.backtest_report,
            "risk_manager": self.risk_manager_report,
        }
        return report_map.get(agent_name.lower())

    def set_report(self, agent_name: str, report: AgentReportDTO) -> None:
        """Set report by agent name."""
        report_map = {
            "macro": "macro_report",
            "fundamental": "fundamental_report",
            "technical": "technical_report",
            "sentiment": "sentiment_report",
            "backtest": "backtest_report",
            "risk_manager": "risk_manager_report",
        }

        key = report_map.get(agent_name.lower())
        if key:
            setattr(self, key, report)

    def get_all_reports(self) -> list[AgentReportDTO]:
        """Get all available reports."""
        reports = []
        for report in [
            self.macro_report,
            self.fundamental_report,
            self.technical_report,
            self.sentiment_report,
            self.backtest_report,
            self.risk_manager_report,
        ]:
            if report:
                reports.append(report)
        return reports

    def get_consensus(self) -> dict[str, Any]:
        """Calculate consensus from all reports."""
        reports = self.get_all_reports()
        if not reports:
            return {"conclusion": "NEUTRAL", "confidence": 0.0}

        bullish = sum(1 for r in reports if "BULLISH" in r.conclusion.upper())
        bearish = sum(1 for r in reports if "BEARISH" in r.conclusion.upper())

        total = len(reports)
        score = (bullish - bearish) / total

        avg_confidence = sum(r.confidence for r in reports) / total

        if score > 0.3:
            conclusion = "BULLISH"
        elif score < -0.3:
            conclusion = "BEARISH"
        else:
            conclusion = "NEUTRAL"

        return {
            "conclusion": conclusion,
            "confidence": avg_confidence,
            "bullish_count": bullish,
            "bearish_count": bearish,
            "total_reports": total,
        }

    def to_legacy_dict(self) -> dict[str, Any]:
        """Convert to legacy dict format for compatibility."""
        result = {
            "ticker": self.ticker,
            "query": self.query,
            "user_id": self.user_id,
            "conversation_log": self.conversation_log,
            "decision_dashboard": self.decision_dashboard,
            "debate_turn": self.debate_turn,
            "investment_debate_history": self.investment_debate_history,
            "risk_debate_turn": self.risk_debate_turn,
            "risk_debate_history": self.risk_debate_history,
            "supervisor_memo": self.supervisor_memo,
        }

        for attr in ["macro", "fundamental", "technical", "sentiment", "backtest", "risk_manager"]:
            report = getattr(self, f"{attr}_report")
            if report:
                result[f"{attr}_report"] = report.narrative
            else:
                result[f"{attr}_report"] = ""

        return result


def create_report_from_agent_response(
    agent_name: str,
    response,
) -> AgentReportDTO:
    """Create AgentReportDTO from AgentResponseDTO."""
    from ..base import AgentResponseDTO, AgentConclusion

    if isinstance(response, AgentResponseDTO):
        conclusion_str = response.conclusion.value if isinstance(response.conclusion, AgentConclusion) else str(response.conclusion)

        return AgentReportDTO(
            agent_name=agent_name,
            conclusion=conclusion_str,
            confidence=response.confidence,
            key_evidence={"evidence_keys": response.evidence_keys},
            narrative=response.narrative,
            timestamp=datetime.now(),
            metadata=response.metadata,
        )

    return AgentReportDTO(
        agent_name=agent_name,
        conclusion="NEUTRAL",
        confidence=0.0,
        narrative=str(response),
    )