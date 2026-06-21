from __future__ import annotations
"""Application service for orchestrating AI Agent analyses."""


import logging
from typing import Any
from app.domain.ports import AgentRepository, AgentLLMPort, MarketDataProvider
from app.domain.agent_entities import MarketInsight, ReportInterpretation
from app.domain.enums import MarketCode
from app.core.logger import get_logger

logger = get_logger(__name__)


class AgenticAnalysisService:
    def __init__(
        self,
        repository: AgentRepository = None,
        llm: AgentLLMPort = None,
        market_data: MarketDataProvider = None
    ):
        self._repository = repository
        self._llm = llm
        self._market_data = market_data

    def get_latest_market_insight(self, market: str = "CN") -> MarketInsight | None:
        insights = self._repository.list_market_insights(market, limit=1)
        return insights[0] if insights else None

    def analyze_current_market(self, market_code: MarketCode = MarketCode.CN) -> MarketInsight:
        """Fetch real-time data and run AI analysis."""
        # 1. Gather raw data
        overview = self._market_data.get_market_overview(market_code)
        rankings = self._market_data.get_market_rankings(market_code)
        
        market_data = {
            "market": market_code.value,
            "overview": overview,
            "top_gainers": rankings.get("gainers", [])[:10]
        }
        
        # 2. Run LLM Agent
        insight = self._llm.analyze_market(market_data)
        
        # 3. Persist
        self._repository.save_market_insight(insight)
        
        return insight

    def interpret_report(self, report_text: str, source: str | None = None) -> ReportInterpretation:
        """Run AI interpretation on a research report."""
        # 1. Run LLM Agent
        interpretation = self._llm.interpret_report(report_text)
        if source:
            interpretation.source = source
            
        # 2. Persist
        self._repository.save_report_interpretation(interpretation)
        
        return interpretation
