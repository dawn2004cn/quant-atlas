from __future__ import annotations
"""LLM implementation for AI Agent operations."""


import json
from typing import Any
from app.domain.ports import AgentLLMPort
from app.domain.agent_entities import MarketInsight, ReportInterpretation
from app.infrastructure.adapters.ollama_prompt_adapter import OllamaPromptAdapter


from app.core.logger import get_logger

logger = get_logger(__name__)


class AgentLLMAdapter(AgentLLMPort):
    def __init__(self, prompt_adapter: OllamaPromptAdapter):
        self._prompt_adapter = prompt_adapter

    def analyze_market(self, market_data: dict[str, Any]) -> MarketInsight:
        prompt = f"""
        Analyze the following market data and provide a structured JSON response.
        Data: {json.dumps(market_data)}

        Required JSON format:
        {{
            "sentiment_score": float (-1.0 to 1.0),
            "sentiment_label": "Greed" | "Fear" | "Neutral",
            "trend_prediction": "Bullish" | "Bearish" | "Sideways",
            "hot_sectors": ["sector1", "sector2"],
            "full_analysis": "your detailed analysis text"
        }}
        """
        response = self._prompt_adapter.generate(prompt)
        try:
            data = self._parse_json(response)
            return MarketInsight(
                market=market_data.get("market", "Unknown"),
                sentiment_score=data.get("sentiment_score", 0.0),
                sentiment_label=data.get("sentiment_label", "Neutral"),
                trend_prediction=data.get("trend_prediction", "Sideways"),
                hot_sectors=data.get("hot_sectors", []),
                full_analysis=data.get("full_analysis", response)
            )
        except Exception as e:
            logger.error(f"Failed to parse LLM market analysis: {e}")
            return MarketInsight(market=market_data.get("market", "Unknown"), full_analysis=response)

    def interpret_report(self, report_text: str) -> ReportInterpretation:
        prompt = f"""
        Interpret the following research report and provide a structured JSON response.
        Report: {report_text[:2000]}  # Limit text length

        Required JSON format:
        {{
            "report_title": "string",
            "summary": "one sentence summary",
            "key_takeaways": ["point1", "point2"],
            "market_impact": "High" | "Medium" | "Low",
            "full_interpretation": "detailed analysis"
        }}
        """
        response = self._prompt_adapter.generate(prompt)
        try:
            data = self._parse_json(response)
            return ReportInterpretation(
                report_title=data.get("report_title", "Untitled"),
                summary=data.get("summary", ""),
                key_takeaways=data.get("key_takeaways", []),
                market_impact=data.get("market_impact", "Low"),
                full_interpretation=data.get("full_interpretation", response)
            )
        except Exception as e:
            logger.error(f"Failed to parse LLM report interpretation: {e}")
            return ReportInterpretation(report_title="Failed to Parse", full_interpretation=response)

    def _parse_json(self, text: str) -> dict:
        # Simple extraction of JSON from markdown or raw text
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "{" in text and "}" in text:
            text = "{" + text.split("{", 1)[1].rsplit("}", 1)[0] + "}"
        return json.loads(text.strip())

    def generate(self, prompt: str, params: dict[str, Any] | None = None) -> str:
        return self._prompt_adapter.generate(prompt)

    def chat(self, messages: list[dict[str, str]], params: dict[str, Any] | None = None) -> str:
        return self._prompt_adapter.chat(messages)
