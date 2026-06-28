from __future__ import annotations

"""Decision Traceability - Attribution Analysis & Decision Heat Map.

This module implements from midify_plan12.md:
- AttributionAnalyzer: Track which evidence influenced final decision
- DecisionHeatMap: Visual representation of decision path
- InfluenceFactor: Quantify evidence contribution to final conclusion

Usage:
    analyzer = AttributionAnalyzer()
    attribution = analyzer.analyze(agent_results, final_conclusion)
    heatmap = DecisionHeatMap(attribution)
    markdown_report = heatmap.to_markdown()
"""


from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from app.core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class InfluenceFactor:
    """Single evidence's influence on final decision."""
    evidence_key: str
    evidence_value: Any
    source_agent: str
    strength: str
    influence_score: float
    contribution_percentage: float
    timestamp: datetime


@dataclass
class DecisionAttribution:
    """Complete attribution of a decision."""
    final_conclusion: str
    final_confidence: float
    influencing_evidence: list[InfluenceFactor]
    agent_contributions: dict[str, float]
    decision_path: list[str]
    generated_at: datetime = field(default_factory=datetime.now)


class AttributionAnalyzer:
    """Analyze which evidence contributed to final decision.

    Provides transparency for human experts in human-agent collaboration.
    """

    def analyze(
        self,
        agent_results: list[dict[str, Any]],
        final_conclusion: str,
        final_confidence: float,
    ) -> DecisionAttribution:
        """Analyze attribution for a decision."""
        influencing_evidence = []
        agent_contributions: dict[str, float] = {}

        for result in agent_results:
            agent_name = result.get("agent_name", "unknown")
            evidence_keys = result.get("evidence_keys", [])
            confidence = result.get("confidence", 0.5)

            agent_weight = confidence * (1.0 if final_conclusion.upper() in result.get("conclusion", "").upper() else 0.5)

            if agent_name not in agent_contributions:
                agent_contributions[agent_name] = 0.0
            agent_contributions[agent_name] += agent_weight

            for key in evidence_keys:
                strength = self._estimate_strength(key, result)

                influence = InfluenceFactor(
                    evidence_key=key,
                    evidence_value=result.get(f"value_{key}", "N/A"),
                    source_agent=agent_name,
                    strength=strength,
                    influence_score=agent_weight,
                    contribution_percentage=0.0,
                    timestamp=datetime.now(),
                )
                influencing_evidence.append(influence)

        total_influence = sum(e.influence_score for e in influencing_evidence)
        if total_influence > 0:
            for e in influencing_evidence:
                e.contribution_percentage = (e.influence_score / total_influence) * 100

        sorted_evidence = sorted(
            influencing_evidence,
            key=lambda x: x.influence_score,
            reverse=True,
        )

        decision_path = self._build_decision_path(agent_results, final_conclusion)

        return DecisionAttribution(
            final_conclusion=final_conclusion,
            final_confidence=final_confidence,
            influencing_evidence=sorted_evidence,
            agent_contributions=agent_contributions,
            decision_path=decision_path,
        )

    def _estimate_strength(self, key: str, result: dict[str, Any]) -> str:
        """Estimate evidence strength from key patterns."""
        high_impact_keywords = ["profit", "cash", "debt", "fraud", "delist"]
        low_impact_keywords = ["sentiment", "social", "news"]

        key_lower = key.lower()
        for kw in high_impact_keywords:
            if kw in key_lower:
                return "strong"
        for kw in low_impact_keywords:
            if kw in key_lower:
                return "weak"

        return "medium"

    def _build_decision_path(
        self,
        agent_results: list[dict[str, Any]],
        final_conclusion: str,
    ) -> list[str]:
        """Build human-readable decision path."""
        path = ["Analysis Start"]

        sorted_results = sorted(
            agent_results,
            key=lambda r: r.get("confidence", 0.5),
            reverse=True,
        )

        for result in sorted_results[:3]:
            agent = result.get("agent_name", "unknown")
            conclusion = result.get("conclusion", "NEUTRAL")
            path.append(f"{agent}: {conclusion}")

        path.append(f"Final Decision: {final_conclusion}")

        return path


class DecisionHeatMap:
    """Generate visual heat map of decision influences."""

    def __init__(self, attribution: DecisionAttribution):
        self._attribution = attribution

    def to_markdown(self) -> str:
        """Generate markdown report with highlighted evidence."""
        lines = []

        lines.append("## 🎯 Decision Heat Map\n")
        lines.append(f"**Final Conclusion:** `{self._attribution.final_conclusion}`")
        lines.append(f"**Confidence:** `{self._attribution.final_confidence:.1%}`\n")

        lines.append("### Evidence Attribution\n")
        lines.append("| Evidence | Source Agent | Strength | Influence |")
        lines.append("|----------|--------------|-----------|------------|")

        for evidence in self._attribution.influencing_evidence[:10]:
            strength_emoji = self._get_strength_emoji(evidence.strength)
            influence_bar = self._get_influence_bar(evidence.contribution_percentage)

            lines.append(
                f"| {evidence.evidence_key} | {evidence.source_agent} "
                f"| {strength_emoji} {evidence.strength} | {influence_bar} {evidence.contribution_percentage:.1f}% |"
            )

        lines.append("\n### Agent Contributions\n")
        sorted_agents = sorted(
            self._attribution.agent_contributions.items(),
            key=lambda x: x[1],
            reverse=True,
        )
        for agent, contribution in sorted_agents:
            bar = self._get_influence_bar(contribution * 100)
            lines.append(f"- **{agent}**: {bar} ({contribution:.2f})")

        lines.append("\n### Decision Path\n")
        for i, step in enumerate(self._attribution.decision_path):
            prefix = "→" if i > 0 else "•"
            lines.append(f"{prefix} {step}")

        return "\n".join(lines)

    def to_html(self) -> str:
        """Generate HTML heat map visualization."""
        html = ['<div class="decision-heatmap">']
        html.append(f'<div class="final-conclusion">{self._attribution.final_conclusion}</div>')

        html.append('<div class="evidence-list">')
        for evidence in self._attribution.influencing_evidence[:8]:
            color = self._get_heatmap_color(evidence.contribution_percentage)
            html.append(f'''
                <div class="evidence-item" style="--heat: {color}">
                    <span class="key">{evidence.evidence_key}</span>
                    <span class="source">{evidence.source_agent}</span>
                    <span class="influence">{evidence.contribution_percentage:.1f}%</span>
                </div>
            ''')
        html.append('</div>')
        html.append('</div>')

        return "\n".join(html)

    def _get_strength_emoji(self, strength: str) -> str:
        """Get emoji for strength level."""
        return {"strong": "🔥", "medium": "⚡", "weak": "❄️"}.get(strength, "•")

    def _get_influence_bar(self, percentage: float) -> str:
        """Get visual influence bar."""
        filled = int(percentage / 10)
        return "█" * filled + "░" * (10 - filled)

    def _get_heatmap_color(self, percentage: float) -> str:
        """Get color for heat map based on influence."""
        if percentage > 30:
            return "#ff4444"
        elif percentage > 15:
            return "#ff8844"
        elif percentage > 5:
            return "#ffcc44"
        else:
            return "#44ff44"


class ExplainableDecision:
    """Complete explainable decision with full traceability."""

    def __init__(
        self,
        attribution: DecisionAttribution,
        heatmap: DecisionHeatMap,
    ):
        self._attribution = attribution
        self._heatmap = heatmap

    def to_full_report(self) -> dict[str, Any]:
        """Generate full explainability report."""
        return {
            "decision": {
                "conclusion": self._attribution.final_conclusion,
                "confidence": self._attribution.final_confidence,
            },
            "attribution": {
                "influencing_evidence": [
                    {
                        "key": e.evidence_key,
                        "source": e.source_agent,
                        "strength": e.strength,
                        "influence_pct": e.contribution_percentage,
                    }
                    for e in self._attribution.influencing_evidence
                ],
                "agent_contributions": self._attribution.agent_contributions,
            },
            "decision_path": self._attribution.decision_path,
            "visualization": {
                "markdown": self._heatmap.to_markdown(),
            },
            "timestamp": self._attribution.generated_at.isoformat(),
        }


def create_attribution_analyzer() -> AttributionAnalyzer:
    """Factory to create attribution analyzer."""
    return AttributionAnalyzer()


def create_decision_heatmap(attribution: DecisionAttribution) -> DecisionHeatMap:
    """Factory to create decision heat map."""
    return DecisionHeatMap(attribution)
