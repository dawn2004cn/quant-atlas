"""AI Agent Service Adapters.

Adapters implement the AI Agent Ports using the current concrete services.
Each adapter wraps an existing service and adapts its interface to match
the corresponding port contract.

This enables:
1. Clean separation between route handlers and service implementations
2. Easy substitution of service implementations in tests
3. Clear migration path to independent microservice
"""

from __future__ import annotations

from typing import Any

from app.modules.ai_agent.ports import (
    AnalysisPort,
    BriefingPort,
    ChartVisionPort,
    ChatPort,
    CommitteePort,
    EvidencePort,
    FinGPTPort,
    HedgeFundPort,
    JarvisPort,
    PromptEvolutionPort,
    ResearchPort,
)


class AnalysisAdapter(AnalysisPort):
    """Adapts AI analysis service to AnalysisPort."""

    def __init__(self, service: Any) -> None:
        self._service = service

    def analyze_stock(self, symbol: str, market: str, query: str) -> dict[str, Any]:
        return self._service.analyze_stock(symbol, market, query)


class EvidenceAdapter(EvidencePort):
    """Adapts AI evidence service to EvidencePort."""

    def __init__(self, service: Any) -> None:
        self._service = service

    def get_evidence(self, symbol: str, market: str) -> dict[str, Any]:
        return self._service.get_evidence(symbol, market)


class ChatAdapter(ChatPort):
    """Adapts AI chat service to ChatPort."""

    def __init__(self, service: Any) -> None:
        self._service = service

    def chat(self, message: str, context: dict[str, Any]) -> dict[str, Any]:
        return self._service.chat(message, context)


class CommitteeAdapter(CommitteePort):
    """Adapts investment committee service to CommitteePort."""

    def __init__(self, service: Any) -> None:
        self._service = service

    def get_decision(self, topic: str) -> dict[str, Any]:
        return self._service.get_decision(topic)


class HedgeFundAdapter(HedgeFundPort):
    """Adapts AI hedge fund service to HedgeFundPort."""

    def __init__(self, service: Any) -> None:
        self._service = service

    def run_simulation(self, params: dict[str, Any]) -> dict[str, Any]:
        return self._service.run_simulation(params)


class FinGPTAdapter(FinGPTPort):
    """Adapts FinGPT service to FinGPTPort."""

    def __init__(self, service: Any) -> None:
        self._service = service

    def get_signal(self, symbol: str) -> dict[str, Any]:
        return self._service.get_signal(symbol)


class BriefingAdapter(BriefingPort):
    """Adapts smart briefing service to BriefingPort."""

    def __init__(self, service: Any) -> None:
        self._service = service

    def get_briefing(self, user_id: int) -> dict[str, Any]:
        return self._service.get_briefing(user_id)


class ChartVisionAdapter(ChartVisionPort):
    """Adapts chart vision service to ChartVisionPort."""

    def __init__(self, service: Any) -> None:
        self._service = service

    def analyze_chart(self, image_data: str, symbol: str) -> dict[str, Any]:
        return self._service.analyze_chart(image_data, symbol)


class JarvisAdapter(JarvisPort):
    """Adapts Jarvis service to JarvisPort."""

    def __init__(self, service: Any) -> None:
        self._service = service

    def query(self, query: str) -> dict[str, Any]:
        return self._service.query(query)


class PromptEvolutionAdapter(PromptEvolutionPort):
    """Adapts prompt evolution service to PromptEvolutionPort."""

    def __init__(self, service: Any) -> None:
        self._service = service

    def evolve(self, feedback: dict[str, Any]) -> dict[str, Any]:
        return self._service.evolve(feedback)


class ResearchAdapter(ResearchPort):
    """Adapts AI research service to ResearchPort."""

    def __init__(self, service: Any) -> None:
        self._service = service

    def research(self, query: str, depth: str = "standard") -> dict[str, Any]:
        return self._service.research(query, depth=depth)


def create_ai_agent_ports(ctx: Any) -> dict[str, Any]:
    """Create all AI agent ports from an ApiV1Context.

    This factory function maps context services to port adapters.
    Returns a dict of port_name -> port_instance.
    """
    ports = {}

    if getattr(ctx, "ai_analysis_service", None) is not None:
        ports["analysis"] = AnalysisAdapter(ctx.ai_analysis_service)

    if getattr(ctx, "ai_evidence_service", None) is not None:
        ports["evidence"] = EvidenceAdapter(ctx.ai_evidence_service)

    if getattr(ctx, "ai_chat_service", None) is not None:
        ports["chat"] = ChatAdapter(ctx.ai_chat_service)

    if getattr(ctx, "investment_committee_service", None) is not None:
        ports["committee"] = CommitteeAdapter(ctx.investment_committee_service)

    if getattr(ctx, "ai_hedge_fund_service", None) is not None:
        ports["hedge_fund"] = HedgeFundAdapter(ctx.ai_hedge_fund_service)

    if getattr(ctx, "fingpt_application_service", None) is not None:
        ports["fingpt"] = FinGPTAdapter(ctx.fingpt_application_service)

    if getattr(ctx, "smart_daily_briefing_service", None) is not None:
        ports["briefing"] = BriefingAdapter(ctx.smart_daily_briefing_service)

    if getattr(ctx, "chart_vision_agent_service", None) is not None:
        ports["chart_vision"] = ChartVisionAdapter(ctx.chart_vision_agent_service)

    if getattr(ctx, "jarvis_proactive_service", None) is not None:
        ports["jarvis"] = JarvisAdapter(ctx.jarvis_proactive_service)

    if getattr(ctx, "prompt_evolution_service", None) is not None:
        ports["prompt_evolution"] = PromptEvolutionAdapter(ctx.prompt_evolution_service)

    if getattr(ctx, "ai_research_service", None) is not None:
        ports["research"] = ResearchAdapter(ctx.ai_research_service)

    return ports


__all__ = [
    "AnalysisPort",
    "EvidencePort",
    "ChatPort",
    "CommitteePort",
    "HedgeFundPort",
    "FinGPTPort",
    "BriefingPort",
    "ChartVisionPort",
    "JarvisPort",
    "PromptEvolutionPort",
    "ResearchPort",
    "AnalysisAdapter",
    "EvidenceAdapter",
    "ChatAdapter",
    "CommitteeAdapter",
    "HedgeFundAdapter",
    "FinGPTAdapter",
    "BriefingAdapter",
    "ChartVisionAdapter",
    "JarvisAdapter",
    "PromptEvolutionAdapter",
    "ResearchAdapter",
    "create_ai_agent_ports",
]
