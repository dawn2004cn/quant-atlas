from __future__ import annotations
"""Integrated Research Graph - Reactive Hierarchical Departments.

This module implements the integration from midify_plan13.md:
- Parallel department execution via TeamSupervisor
- Evidence-driven early exit via EvidenceRouter
- LLM tiered scheduling via TieredLLMOrchestrator
- Meta-learning closed loop via WeightedAggregator
- Global tool wrapper via EvidenceAwareToolWrapper

Usage:
    graph = build_integrated_research_graph(llm)
    result = await graph.ainvoke({"ticker": "600519", "query": "分析"})
"""


import asyncio
from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import MemorySaver

from ..constants import (
    AgentName,
    get_llm_tier_for_agent,
    CRITICAL_RISK_KEYS,
    TOOL_CONTEXT_LIMITS,
)
from ..evidence_blackboard import (
    get_evidence_blackboard,
    EvidenceType,
    EvidenceStrength,
)
from ..evidence_router import EvidenceRouter
from ..dynamic_weighting import WeightedAggregator
from ..tiered_llm import TieredLLMOrchestrator
from ..auto_validator import AutoValidator
from .state import ResearchState
from .topology_compiler import TopologyCompiler

from app.core.logger import get_logger
from app.domain.swarm_topology_presets import PRESET_REGISTRY, preset_integrated_parallel
from app.domain.topology_schema import SwarmTopologyDescriptor


logger = get_logger(__name__)


class IntegratedResearchGraph:
    """Integrated research graph with all advanced features.

    Features:
    - Parallel department execution
    - Evidence-driven early exit
    - LLM tiered scheduling
    - Meta-learning closed loop
    - Structured evidence communication
    """

    def __init__(
        self,
        llm: BaseChatModel,
        checkpointer: BaseCheckpointSaver | None = None,
    ):
        self._llm = llm
        self._checkpointer = checkpointer or MemorySaver()
        self._blackboard = get_evidence_blackboard()
        self._evidence_router = EvidenceRouter()
        self._weighted_aggregator = WeightedAggregator()
        self._llm_orchestrator = TieredLLMOrchestrator()
        self._auto_validator = AutoValidator()

    async def execute_supervisor(self, state: ResearchState) -> dict[str, Any]:
        """Execute supervisor with LLM tiered scheduling."""
        from .react_loop import react_with_tools

        ticker = state.get("ticker", "")
        query = state.get("query", "")

        sys = """你是 **Supervisor Orchestrator**（研究编排者）??阅读用户问题与标的，输出简洁的「研究计划」??"""
        user = f"ticker={ticker}, query={query}"

        get_llm_tier_for_agent(AgentName.SUPERVISOR)
        result = await react_with_tools(self._llm, [], system=sys, user=user, max_rounds=1)

        # Publish perception vector for cross-node resonance (10.0)
        if ticker:
            try:
                from app.core.mesh.perception_bridge import publish_perception, subscribe_perception

                # Publish research start signal
                publish_perception(
                    text=f"research_started:{ticker}:{query[:50]}",
                    metadata={
                        "type": "research_start",
                        "symbol": ticker,
                        "query": query[:100],
                    },
                    ttl_seconds=600,
                )

                # Subscribe to related signals
                subscribe_perception(
                    text=f"risk_alert:{ticker}",
                    threshold=0.75,
                    label=f"risk_alerts_for_{ticker}",
                )
                subscribe_perception(
                    text=f"currency_risk:{ticker[:3] if len(ticker) >= 6 else 'CN'}",
                    threshold=0.7,
                    label=f"currency_risk_for_{ticker}",
                )

                logger.debug("perception layer: published research_start and subscribed for %s", ticker)
            except Exception as exc:
                logger.debug("perception layer integration skipped: %s", exc)

        return {"supervisor_memo": result, "debate_turn": 0}

    async def execute_parallel_departments(self, state: ResearchState) -> dict[str, Any]:
        """Execute all departments in parallel using TeamSupervisor pattern."""
        from .react_loop import react_with_tools

        async def run_macro():
            sys = "你是 Macro Analyst - 宏观分析?"
            user = f"标的: {state.get('ticker')}"
            return ("macro_report", await react_with_tools(self._llm, [], system=sys, user=user))

        async def run_fundamental():
            sys = "你是 Fundamental Analyst - 基本面分析师"
            user = f"标的: {state.get('ticker')}, 宏观: {state.get('macro_report', '')[:TOOL_CONTEXT_LIMITS['macro_report']]}"
            return ("fundamental_report", await react_with_tools(self._llm, [], system=sys, user=user))

        async def run_technical():
            sys = "你是 Technical Analyst - 技术分析师"
            user = f"标的: {state.get('ticker')}, 基本?? {state.get('fundamental_report', '')[:TOOL_CONTEXT_LIMITS['fundamental_report']]}"
            return ("technical_report", await react_with_tools(self._llm, [], system=sys, user=user))

        async def run_sentiment():
            sys = "你是 Sentiment Analyst - 情绪分析?"
            user = f"标的: {state.get('ticker')}, 技?? {state.get('technical_report', '')[:TOOL_CONTEXT_LIMITS['technical_report']]}"
            return ("sentiment_report", await react_with_tools(self._llm, [], system=sys, user=user))

        async def run_backtest():
            sys = "你是 Backtest Analyst - 回测分析?"
            user = f"标的: {state.get('ticker')}"
            return ("backtest_report", await react_with_tools(self._llm, [], system=sys, user=user))

        results = await asyncio.gather(
            run_macro(),
            run_fundamental(),
            run_technical(),
            run_sentiment(),
            run_backtest(),
            return_exceptions=True
        )

        reports = {}
        for r in results:
            if isinstance(r, tuple):
                key, value = r
                reports[key] = value
            elif isinstance(r, Exception):
                logger.error(f"Department failed: {r}")

        return reports

    async def _run_single_analyst(self, role: str, state: ResearchState) -> dict[str, Any]:
        """Run one analyst department (for sequential / debate topologies)."""
        from .react_loop import react_with_tools

        prompts = {
            "macro": "你是 Macro Analyst - 宏观分析?",
            "fundamental": "你是 Fundamental Analyst - 基本面分析师",
            "technical": "你是 Technical Analyst - 技术分析师",
            "sentiment": "你是 Sentiment Analyst - 情绪分析?",
            "backtest": "你是 Backtest Analyst - 回测分析?",
        }
        sys = prompts.get(role, f"你是 {role} 分析?")
        user = f"标的: {state.get('ticker')}, query={state.get('query', '')}"
        report = await react_with_tools(self._llm, [], system=sys, user=user)
        key = f"{role}_report" if role != "backtest" else "backtest_report"
        if role == "macro":
            key = "macro_report"
        return {key: report}

    async def execute_macro_analyst(self, state: ResearchState) -> dict[str, Any]:
        return await self._run_single_analyst("macro", state)

    async def execute_fundamental_analyst(self, state: ResearchState) -> dict[str, Any]:
        return await self._run_single_analyst("fundamental", state)

    async def execute_technical_analyst(self, state: ResearchState) -> dict[str, Any]:
        return await self._run_single_analyst("technical", state)

    async def execute_sentiment_analyst(self, state: ResearchState) -> dict[str, Any]:
        return await self._run_single_analyst("sentiment", state)

    async def execute_backtest_analyst(self, state: ResearchState) -> dict[str, Any]:
        return await self._run_single_analyst("backtest", state)

    async def execute_debate_node(self, role: str, state: ResearchState) -> dict[str, Any]:
        """Lightweight debate hop ??publishes DebateRoundEvent when possible."""
        from .debate_bus import publish_debate_round
        from .react_loop import react_with_tools

        stance = "bullish" if "bull" in (role or "").lower() else "bearish"
        sys = f"你是 {'多头' if stance == 'bullish' else '空头'} 辩论员，给出简洁论点?"
        user = f"标的: {state.get('ticker')}, 技?? {(state.get('technical_report') or '')[:400]}"
        memo = await react_with_tools(self._llm, [], system=sys, user=user, max_rounds=1)
        try:
            publish_debate_round(
                symbol=str(state.get("ticker") or ""),
                market="CN",
                role=stance,
                content=memo,
                debate_phase="investment",
            )
        except Exception as exc:  # noqa: BLE001
            logger.debug("debate node publish: %s", exc)
        key = "bull_debate_memo" if stance == "bullish" else "bear_debate_memo"
        return {key: memo, "debate_turn": int(state.get("debate_turn") or 0) + 1}

    async def execute_arbiter_node(self, state: ResearchState) -> dict[str, Any]:
        """Final arbiter consensus before synthesis."""
        from .react_loop import react_with_tools

        sys = "你是 Final Arbiter，综合多空辩论与分析师报告，给出 verdict 与置信度?"
        user = (
            f"ticker={state.get('ticker')}, bull={state.get('bull_debate_memo', '')[:300]}, "
            f"bear={state.get('bear_debate_memo', '')[:300]}"
        )
        memo = await react_with_tools(self._llm, [], system=sys, user=user, max_rounds=1)
        return {"arbiter_memo": memo}

    async def execute_evidence_routing(self, state: ResearchState) -> dict[str, Any]:
        """Execute evidence-driven routing with early exit."""
        ticker = state.get("ticker", "")

        has_critical_risk = False
        for key in CRITICAL_RISK_KEYS:
            evidence = await self._blackboard.read_evidence(ticker, key)
            if evidence:
                has_critical_risk = True
                logger.warning(f"Critical risk detected: {key}")
                await self._blackboard.write_evidence(
                    ticker,
                    "critical_risk_detected",
                    True,
                    EvidenceType.RISK,
                    EvidenceStrength.STRONG,
                    "evidence_routing",
                )
                break

        routing_decision = self._evidence_router.route(
            state.get("ticker", ""),
            state.get("macro_report", ""),
            state.get("fundamental_report", ""),
        )

        return {
            "should_skip_backtest": has_critical_risk or routing_decision.get("skip_backtest", False),
            "should_skip_sentiment": routing_decision.get("skip_sentiment", False),
            "routing_decision": routing_decision,
        }

    async def execute_risk_manager(self, state: ResearchState) -> dict[str, Any]:
        """Execute risk manager with weighted aggregation."""
        from .react_loop import react_with_tools

        agent_results = []
        for key in ["macro", "fundamental", "technical", "sentiment", "backtest"]:
            report = state.get(f"{key}_report", "")
            if report:
                agent_results.append({
                    "agent_name": f"{key.capitalize()}Analyst",
                    "conclusion": "BULLISH" if "看涨" in report or "bullish" in report.lower() else "BEARISH",
                    "confidence": 0.7,
                    "evidence_keys": [],
                })

        weighted_result = self._weighted_aggregator.aggregate_with_accuracy_weight(agent_results)

        sys = f"""你是 Risk Manager - 风险管理者??基于加权共识: {weighted_result.final_conclusion}, 置信?? {weighted_result.final_confidence:.2f}
元学习备? {weighted_result.meta_learning_note or 'N/A'}
"""
        user = f"标的: {state.get('ticker')}, 做最终风险评?"

        report = await react_with_tools(self._llm, [], system=sys, user=user)

        return {"risk_manager_report": report}

    async def execute_synthesis(self, state: ResearchState) -> dict[str, Any]:
        """Execute synthesis with decision traceability."""
        from .react_loop import react_with_tools

        agent_results = []
        for key in ["macro", "fundamental", "technical", "sentiment", "backtest", "risk", "chart_vision"]:
            report = state.get(f"{key}_report", "")
            if report:
                conclusion = "BULLISH"
                if "看跌" in report or "bearish" in report.lower() or "downtrend" in report.lower():
                    conclusion = "BEARISH"
                elif "中?" in report or "neutral" in report.lower() or "sideways" in report.lower():
                    conclusion = "NEUTRAL"

                confidence = 0.7
                if key == "chart_vision":
                    confidence = state.get("chart_vision_confidence", 0.7)

                agent_results.append({
                    "agent_name": f"{key.replace('_', ' ').title().replace(' ', '')}Analyst",
                    "conclusion": conclusion,
                    "confidence": confidence,
                    "evidence_keys": [],
                    "raw_report": report[:500],
                })

        weighted_result = self._weighted_aggregator.aggregate_with_accuracy_weight(agent_results)

        from ..decision_traceability import create_attribution_analyzer, create_decision_heatmap

        analyzer = create_attribution_analyzer()
        attribution = analyzer.analyze(
            agent_results,
            weighted_result.final_conclusion,
            weighted_result.final_confidence,
        )
        heatmap = create_decision_heatmap(attribution)

        sys = f"""你是 Synthesis Service - 综合服务??最终结?? {weighted_result.final_conclusion}, 置信?? {weighted_result.final_confidence:.2f}
决策热力
{heatmap.to_markdown()}
"""
        user = f"标的: {state.get('ticker')}, 生成最终投资建?"

        report = await react_with_tools(self._llm, [], system=sys, user=user)

        return {
            "decision_dashboard": report,
            "final_verdict": weighted_result.final_conclusion,
            "final_confidence": weighted_result.final_confidence,
            "decision_heatmap": heatmap.to_markdown(),
        }

    async def execute_chart_vision(self, state: ResearchState) -> dict[str, Any]:
        """Execute Chart-Vision Agent ??visual pattern recognition on K-line charts (10.0).

        This node renders a K-line chart from market data, analyzes it with a multimodal
        LLM to identify visual patterns, and merges results with numerical pattern detection.
        """
        ticker = state.get("ticker", "")
        if not ticker:
            return {"chart_vision_report": "No ticker provided for vision analysis"}

        try:
            from app.modules.ai_agent.services.vision.chart_vision_agent_service import ChartVisionAgentService
            from app.modules.market_data.services.stock_service import StockApplicationService
            from app.modules.system.services.helpers.market_data_provider import get_market_data_provider

            market_provider = get_market_data_provider()
            stock_service = StockApplicationService(market_provider=market_provider)
            vision_service = ChartVisionAgentService(stock_service=stock_service)

            result = await asyncio.to_thread(
                vision_service.analyze,
                symbol=ticker,
                market="CN",
                days=120,
                indicators=["ma5", "ma20", "ma60"],
            )

            if result.get("status") != "success":
                return {
                    "chart_vision_report": f"Vision analysis failed: {result.get('message', 'unknown')}",
                    "chart_vision_signal": "neutral",
                    "chart_vision_confidence": 0.0,
                }

            merged = result.get("merged_signal", {})
            visual = result.get("visual_analysis", {})
            numerical = result.get("numerical_analysis", {})

            patterns_desc = []
            for p in visual.get("patterns", []):
                patterns_desc.append(f"{p.get('name', '?')}(置信度{p.get('confidence', 0):.0%})")
            for p in numerical.get("patterns", []):
                patterns_desc.append(f"{p.get('name', '?')}(数??置信度{p.get('confidence', 0):.0%})")

            report_parts = [
                f"视觉趋势: {visual.get('trend', 'unknown')}",
                f"数值趋?? {numerical.get('trend', 'unknown')}",
                f"融合信号: {merged.get('signal', 'neutral')}(置信度{merged.get('confidence', 0):.0%})",
                f"共识: {'视觉与数值一' if merged.get('agreement') else '视觉与数值分'}",
            ]
            if patterns_desc:
                report_parts.append(f"识别形?? {', '.join(patterns_desc)}")
            if visual.get("support_levels"):
                report_parts.append(f"支撑?? {visual['support_levels']}")
            if visual.get("resistance_levels"):
                report_parts.append(f"阻力?? {visual['resistance_levels']}")
            if visual.get("reasoning"):
                report_parts.append(f"分析推理: {visual['reasoning']}")

            report = "\n".join(report_parts)

            try:
                from .debate_bus import publish_debate_round
                publish_debate_round(
                    symbol=ticker,
                    market="CN",
                    role="chart_vision",
                    content=report[:500],
                    debate_phase="vision",
                )
            except Exception as exc:
                logger.debug("chart vision debate publish: %s", exc)

            # Publish perception vector for cross-node resonance (10.0)
            try:
                from app.core.mesh.perception_bridge import publish_perception

                # Publish significant patterns as perception vectors
                signal = merged.get("signal", "neutral")
                confidence = merged.get("confidence", 0.0)

                # Only publish high-confidence signals
                if confidence >= 0.7 and signal != "neutral":
                    perception_text = f"chart_pattern:{ticker}:{signal}"
                    if patterns_desc:
                        perception_text += f":{','.join(patterns_desc[:3])}"

                    publish_perception(
                        text=perception_text,
                        metadata={
                            "type": "chart_vision_signal",
                            "symbol": ticker,
                            "signal": signal,
                            "confidence": confidence,
                            "patterns": patterns_desc[:5],
                            "trend_visual": visual.get("trend", "unknown"),
                            "trend_numerical": numerical.get("trend", "unknown"),
                        },
                        ttl_seconds=600,
                    )
                    logger.debug("published chart_vision perception for %s: %s (conf=%.2f)",
                               ticker, signal, confidence)
            except Exception as exc:
                logger.debug("perception layer publish skipped: %s", exc)

            return {
                "chart_vision_report": report,
                "chart_vision_signal": merged.get("signal", "neutral"),
                "chart_vision_confidence": merged.get("confidence", 0.0),
                "chart_vision_patterns": [p.get("name") for p in visual.get("patterns", [])],
            }

        except Exception as exc:
            logger.error("Chart-Vision Agent failed for %s: %s", ticker, exc)
            return {
                "chart_vision_report": f"Chart-Vision Agent error: {exc}",
                "chart_vision_signal": "neutral",
                "chart_vision_confidence": 0.0,
            }


def resolve_topology(
    topology: SwarmTopologyDescriptor | str | dict | None = None,
    *,
    regime: str | None = None,
    symbol: str = "",
) -> SwarmTopologyDescriptor:
    """Resolve preset id, dict payload, regime-based generation, or default integrated topology.

    Priority:
    1. Explicit topology (SwarmTopologyDescriptor or preset id)
    2. Dict payload (model_validate)
    3. Regime-based generation via TopologyGenerator
    4. Default integrated_parallel preset
    """
    if topology is not None:
        if isinstance(topology, SwarmTopologyDescriptor):
            return topology
        if isinstance(topology, str):
            preset = PRESET_REGISTRY.get(topology)
            if preset is None:
                raise ValueError(f"unknown topology preset: {topology}")
            return preset
        if isinstance(topology, dict):
            return SwarmTopologyDescriptor.model_validate(topology)

    if regime:
        from app.application.services.orchestration.topology_generator import TopologyGenerator

        generator = TopologyGenerator()
        return generator.generate_from_regime(regime, symbol=symbol)

    return preset_integrated_parallel()


def build_integrated_research_graph(
    llm: BaseChatModel,
    *,
    checkpointer: BaseCheckpointSaver | None = None,
    topology: SwarmTopologyDescriptor | str | dict | None = None,
    regime: str | None = None,
    symbol: str = "",
):
    """Build integrated research graph ??statically or from JSON topology descriptor.

    Args:
        llm: Language model for agent execution
        checkpointer: Optional LangGraph checkpointer
        topology: Explicit topology (descriptor, preset id, or dict)
        regime: Market regime for auto-generation (e.g., "high_volatility", "trending")
        symbol: Symbol context for topology generation
    """
    integrated = IntegratedResearchGraph(llm, checkpointer)
    topo = resolve_topology(topology, regime=regime, symbol=symbol)
    compiler = TopologyCompiler(integrated)
    validation = compiler.validate(topo)
    if not validation.get("ok"):
        logger.warning(
            "topology compile has unsupported nodes: %s",
            validation.get("unsupported_nodes"),
        )
    return compiler.compile(topo, state_type=ResearchState, checkpointer=checkpointer)
