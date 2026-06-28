from __future__ import annotations
from app.domain.dto.service_result import GenericResponseDTO
from app.core.registry import register_service
"""Investment Committee multi-agent service - implements consensus mechanism.

This module implements the multi-agent consensus mechanism from midify_plan7.md:
- TechnicalAgent: Analyzes price patterns, trends, indicators
- FundamentalAgent: Analyzes financial statements, earnings, valuation
- SentimentAgent: Analyzes news, social sentiment, market mood
- SynthesisService: Combines all opinions into final decision
"""


from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


from app.core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class AgentOpinion:
    """Opinion from a single agent."""
    agent_name: str
    conclusion: str
    confidence: float
    reasoning: str
    data_sources: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    decision_factors: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class AgentResult:
    """Raw result from an agent before opinion formation."""
    agent_name: str
    raw_data: object
    indicators: dict[str, Any] = field(default_factory=dict)


@dataclass
class DecisionNode:
    """Single node in the decision tree."""
    node_id: str
    factor: str
    value: object
    operator: str
    result: str
    weight: float = 1.0


@dataclass
class DecisionTree:
    """Decision tree representing the reasoning path."""
    root: str = ""
    nodes: list[DecisionNode] = field(default_factory=list)
    final_path: list[str] = field(default_factory=list)

    def to_dict(self) -> GenericResponseDTO:
        """Convert to dictionary for JSON serialization."""
        return {
            "root": self.root,
            "nodes": [
                {
                    "node_id": n.node_id,
                    "factor": n.factor,
                    "value": str(n.value),
                    "operator": n.operator,
                    "result": n.result,
                    "weight": n.weight,
                }
                for n in self.nodes
            ],
            "final_path": self.final_path,
        }


@dataclass
class CommitteeDecision:
    """Final decision from the investment committee."""
    symbol: str
    final_verdict: str
    confidence: float
    consensus_score: float
    agent_opinions: list[AgentOpinion] = field(default_factory=list)
    summary: str = ""
    synthesis_reasoning: str = ""
    decision_tree: DecisionTree | None = None
    evaluation_timestamp: str = ""


@register_service(name="investment_committee_service")
class InvestmentCommitteeService:
    """Multi-agent system for investment decision making with consensus mechanism.

    This service orchestrates multiple specialized agents and synthesizes
    their opinions into a unified investment decision.
    """

    def __init__(
        self,
        llm_adapter: object = None,
        stock_service: object = None,
        market_provider: object = None,
        ai_result_cache: object = None,
    ):
        self._llm = llm_adapter
        self._stock_service = stock_service
        self._market_provider = market_provider
        self._ai_cache = ai_result_cache

    def evaluate_stock(self, symbol: str, market: str = "CN") -> CommitteeDecision:
        """Run investment committee evaluation for a stock with multi-agent consensus."""

        cached = self._check_cache(symbol, market)
        if cached:
            logger.info(f"Using cached committee decision for {symbol}")
            return cached

        technical_result = self._run_technical_agent(symbol, market)
        fundamental_result = self._run_fundamental_agent(symbol, market)
        sentiment_result = self._run_sentiment_agent(symbol, market)

        technical_opinion = self._form_technical_opinion(technical_result)
        fundamental_opinion = self._form_fundamental_opinion(fundamental_result)
        sentiment_opinion = self._form_sentiment_opinion(sentiment_result)

        critic_opinion = self._run_critic_agent(
            symbol, market,
            [technical_opinion, fundamental_opinion, sentiment_opinion]
        )

        opinions = [technical_opinion, fundamental_opinion, sentiment_opinion, critic_opinion]

        synthesis_reasoning = self._synthesize_opinions(opinions)
        final_verdict, consensus_score, decision_tree = self._calculate_verdict(opinions)
        avg_confidence = sum(o.confidence for o in opinions) / len(opinions)

        summary = (
            f"Committee evaluated {symbol}: "
            f"Technical={technical_opinion.conclusion}, "
            f"Fundamental={fundamental_opinion.conclusion}, "
            f"Sentiment={sentiment_opinion.conclusion}. "
            f"Consensus: {consensus_score:.2f}, Verdict: {final_verdict}"
        )

        decision = CommitteeDecision(
            symbol=symbol,
            final_verdict=final_verdict,
            confidence=avg_confidence,
            consensus_score=consensus_score,
            agent_opinions=opinions,
            summary=summary,
            synthesis_reasoning=synthesis_reasoning,
            decision_tree=decision_tree,
            evaluation_timestamp=datetime.now().isoformat(),
        )

        self._cache_result(symbol, market, decision)
        return decision

    def _check_cache(self, symbol: str, market: str) -> CommitteeDecision | None:
        """Check if recent analysis exists in cache."""
        if self._ai_cache:
            return self._ai_cache.get_cached_result("committee", symbol, {"market": market})
        return None

    def _cache_result(self, symbol: str, market: str, decision: CommitteeDecision) -> None:
        """Cache the committee decision."""
        if self._ai_cache:
            self._ai_cache.save_result("committee", symbol, {"market": market}, decision)

    def _run_technical_agent(self, symbol: str, market: str) -> AgentResult:
        """Run technical analysis agent."""
        try:
            history = self._stock_service.get_stock_history(symbol, market, "6mo") if self._stock_service else []

            indicators = {}
            if history:
                prices = [h.get("close", 0) for h in history if h.get("close")]
                volumes = [h.get("volume", 0) for h in history if h.get("volume")]

                if prices:
                    current = prices[-1]
                    ma5 = sum(prices[-5:]) / min(5, len(prices))
                    ma20 = sum(prices[-20:]) / min(20, len(prices)) if len(prices) >= 20 else ma5

                    indicators = {
                        "current_price": current,
                        "ma5": ma5,
                        "ma20": ma20,
                        "trend": "up" if current > ma20 else "down",
                        "momentum": "strong" if abs(current - ma20) / ma20 > 0.05 else "weak",
                        "volume_avg": sum(volumes[-20:]) / min(20, len(volumes)) if volumes else 0,
                    }

            return AgentResult(
                agent_name="TechnicalAgent",
                raw_data={"history": history},
                indicators=indicators,
            )
        except Exception as e:
            logger.warning(f"TechnicalAgent failed for {symbol}: {e}")
            return AgentResult(agent_name="TechnicalAgent", raw_data={}, indicators={})

    def _run_fundamental_agent(self, symbol: str, market: str) -> AgentResult:
        """Run fundamental analysis agent."""
        try:
            profile = {}
            if self._market_provider:
                profile = self._market_provider.get_stock_profile(symbol, market) or {}

            pe = profile.get("pe", 0)
            pb = profile.get("pb", 0)
            market_cap = profile.get("total_market_cap", 0)

            indicators = {
                "pe": pe,
                "pb": pb,
                "market_cap": market_cap,
                "valuation": "overvalued" if pe > 30 else ("undervalued" if pe < 15 else "fair"),
            }

            return AgentResult(
                agent_name="FundamentalAgent",
                raw_data={"profile": profile},
                indicators=indicators,
            )
        except Exception as e:
            logger.warning(f"FundamentalAgent failed for {symbol}: {e}")
            return AgentResult(agent_name="FundamentalAgent", raw_data={}, indicators={})

    def _run_sentiment_agent(self, symbol: str, market: str) -> AgentResult:
        """Run sentiment analysis agent."""
        try:
            news = []
            if self._stock_service:
                news_data = self._stock_service.get_stock_news(symbol, market)
                news = news_data[:10] if news_data else []

            sentiment_score = 0
            if news:
                positive = sum(1 for n in news if any(
                    kw in str(n.get("title", "")).lower()
                    for kw in ["上涨", "增长", "利好", "突破", "业绩", "超预期"]
                ))
                negative = sum(1 for n in news if any(
                    kw in str(n.get("title", "")).lower()
                    for kw in ["下跌", "风险", "利空", "亏损", "警告"]
                ))
                sentiment_score = (positive - negative) / max(len(news), 1)

            indicators = {
                "news_count": len(news),
                "sentiment_score": sentiment_score,
                "sentiment": "bullish" if sentiment_score > 0.2 else ("bearish" if sentiment_score < -0.2 else "neutral"),
            }

            return AgentResult(
                agent_name="SentimentAgent",
                raw_data={"news": news},
                indicators=indicators,
            )
        except Exception as e:
            logger.warning(f"SentimentAgent failed for {symbol}: {e}")
            return AgentResult(agent_name="SentimentAgent", raw_data={}, indicators={})

    def _form_technical_opinion(self, result: AgentResult) -> AgentOpinion:
        """Form opinion from technical analysis results."""
        indicators = result.indicators

        trend = indicators.get("trend", "unknown")
        momentum = indicators.get("momentum", "unknown")

        if trend == "up" and momentum == "strong":
            conclusion = "BULLISH"
            confidence = 0.75
            reasoning = "Price above MA20 with strong momentum, uptrend confirmed."
        elif trend == "down" and momentum == "strong":
            conclusion = "BEARISH"
            confidence = 0.75
            reasoning = "Price below MA20 with strong momentum, downtrend confirmed."
        elif trend == "up":
            conclusion = "SLIGHTLY_BULLISH"
            confidence = 0.55
            reasoning = "Price above MA20 but momentum is weak."
        elif trend == "down":
            conclusion = "SLIGHTLY_BEARISH"
            confidence = 0.55
            reasoning = "Price below MA20 but momentum is weak."
        else:
            conclusion = "NEUTRAL"
            confidence = 0.5
            reasoning = "Insufficient data for technical analysis."

        return AgentOpinion(
            agent_name="TechnicalAgent",
            conclusion=conclusion,
            confidence=confidence,
            reasoning=reasoning,
            data_sources=["Price history", "Moving averages", "Volume"],
            metadata=indicators,
        )

    def _form_fundamental_opinion(self, result: AgentResult) -> AgentOpinion:
        """Form opinion from fundamental analysis results."""
        indicators = result.indicators
        valuation = indicators.get("valuation", "unknown")

        if valuation == "undervalued":
            conclusion = "BULLISH"
            confidence = 0.7
            reasoning = f"PE ratio {indicators.get('pe', 'N/A')} suggests undervaluation."
        elif valuation == "overvalued":
            conclusion = "BEARISH"
            confidence = 0.7
            reasoning = f"PE ratio {indicators.get('pe', 'N/A')} suggests overvaluation."
        else:
            conclusion = "NEUTRAL"
            confidence = 0.5
            reasoning = f"PE ratio {indicators.get('pe', 'N/A')} indicates fair valuation."

        return AgentOpinion(
            agent_name="FundamentalAgent",
            conclusion=conclusion,
            confidence=confidence,
            reasoning=reasoning,
            data_sources=["Financial profile", "Valuation metrics"],
            metadata=indicators,
        )

    def _form_sentiment_opinion(self, result: AgentResult) -> AgentOpinion:
        """Form opinion from sentiment analysis results."""
        indicators = result.indicators
        sentiment = indicators.get("sentiment", "neutral")
        sentiment_score = indicators.get("sentiment_score", 0)

        if sentiment == "bullish":
            conclusion = "BULLISH"
            confidence = 0.65
            reasoning = f"Positive news sentiment (score: {sentiment_score:.2f})."
        elif sentiment == "bearish":
            conclusion = "BEARISH"
            confidence = 0.65
            reasoning = f"Negative news sentiment (score: {sentiment_score:.2f})."
        else:
            conclusion = "NEUTRAL"
            confidence = 0.5
            reasoning = "Neutral or mixed news sentiment."

        return AgentOpinion(
            agent_name="SentimentAgent",
            conclusion=conclusion,
            confidence=confidence,
            reasoning=reasoning,
            data_sources=["News articles", "Social media"],
            metadata=indicators,
        )

    def _run_critic_agent(
        self,
        symbol: str,
        market: str,
        other_opinions: list[AgentOpinion],
    ) -> AgentOpinion:
        """Critic agent validates and weights other agents' conclusions."""
        if not other_opinions:
            return AgentOpinion(
                agent_name="CriticAgent",
                conclusion="NEUTRAL",
                confidence=0.5,
                reasoning="No other opinions to validate.",
                data_sources=["Cross-validation"],
            )

        bullish_count = sum(
            1 for o in other_opinions
            if "BULLISH" in o.conclusion
        )
        bearish_count = sum(
            1 for o in other_opinions
            if "BEARISH" in o.conclusion
        )

        sum(o.confidence for o in other_opinions) / len(other_opinions)

        if abs(bullish_count - bearish_count) >= 2:
            confidence = 0.8
            reasoning = "Strong consensus among agents."
        else:
            confidence = 0.6
            reasoning = "Mixed signals from agents, moderate confidence."

        return AgentOpinion(
            agent_name="CriticAgent",
            conclusion="NEUTRAL",
            confidence=confidence,
            reasoning=reasoning,
            data_sources=["Cross-validation", "Consensus checking"],
        )

    def _synthesize_opinions(self, opinions: list[AgentOpinion]) -> str:
        """Synthesize all opinions into coherent reasoning using LLM."""
        if not self._llm:
            return "Synthesis based on weighted average of agent opinions."

        try:
            opinion_summary = "\n".join([
                f"- {o.agent_name}: {o.conclusion} (conf: {o.confidence:.2f})"
                for o in opinions
            ])

            prompt = f"""Synthesize the following agent opinions for stock analysis:

{opinion_summary}

Provide a brief synthesis reasoning (2-3 sentences):"""

            return self._llm.generate(prompt, {"max_tokens": 150}) or "Synthesis complete."
        except Exception as e:
            logger.warning(f"LLM synthesis failed: {e}")
            return "Synthesis based on weighted average of agent opinions."

    def _calculate_verdict(self, opinions: list[AgentOpinion]) -> tuple[str, float, DecisionTree]:
        """Calculate final verdict from agent opinions with decision tree."""
        positive_count = 0
        negative_count = 0
        total_weight = 0.0

        decision_nodes = []
        node_counter = 0

        for opinion in opinions:
            weight = opinion.confidence
            total_weight += weight

            decision_nodes.append(DecisionNode(
                node_id=f"node_{node_counter}",
                factor=opinion.agent_name,
                value=opinion.conclusion,
                operator="evaluate",
                result="positive" if "BULLISH" in opinion.conclusion else ("negative" if "BEARISH" in opinion.conclusion else "neutral"),
                weight=weight,
            ))
            node_counter += 1

            if "BULLISH" in opinion.conclusion:
                positive_count += weight
            elif "BEARISH" in opinion.conclusion:
                negative_count += weight

        if total_weight > 0:
            consensus_score = (positive_count - negative_count) / total_weight
        else:
            consensus_score = 0.0

        if consensus_score > 0.3:
            final_verdict = "STRONG_BUY"
        elif consensus_score > 0:
            final_verdict = "BUY"
        elif consensus_score < -0.3:
            final_verdict = "STRONG_SELL"
        elif consensus_score < 0:
            final_verdict = "SELL"
        else:
            final_verdict = "HOLD"

        final_path = [f"Collected {len(opinions)} agent opinions", f"Calculated consensus: {consensus_score:.2f}", f"Final verdict: {final_verdict}"]

        decision_tree = DecisionTree(
            root=final_verdict,
            nodes=decision_nodes,
            final_path=final_path,
        )

        return final_verdict, consensus_score, decision_tree
