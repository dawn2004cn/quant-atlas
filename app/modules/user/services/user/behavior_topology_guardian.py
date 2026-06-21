from __future__ import annotations

from typing import Any, Dict, Optional
from app.core.logger import get_logger

logger = get_logger(__name__)


def enrich_psychology_with_topology(
    payload: Dict[str, Any],
    user_knowledge_service: Any | None = None,
    user_id: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Enriches psychology guardian results with behavior topology context.

    If user_knowledge_service is provided, calls analyze_topology() to fetch
    real bias/fatigue/alert data and merges it into the payload.
    """
    topology_context: Dict[str, Any] = {
        "cluster_risk": "stable",
        "bias_type": "neutral",
        "topology_score": 0.5,
        "message": "No significant behavioral topology anomalies detected.",
    }
    merged_alerts: list = list(payload.get("alerts", []))
    merged_biases: list = []
    fatigue_level: str = "low"

    if user_id is None:
        payload["topology_context"] = topology_context
        payload["alerts"] = merged_alerts
        return payload

    try:
        if user_knowledge_service and hasattr(user_knowledge_service, "analyze_topology"):
            topo = user_knowledge_service.analyze_topology(user_id)
            if isinstance(topo, dict):
                fatigue_level = topo.get("fatigue_level", "low")
                merged_alerts.extend(topo.get("alerts", []))
                merged_biases = topo.get("cognitive_biases", [])

                # Compute an overall topology score from fatigue + bias count
                score_map = {"low": 0.3, "medium": 0.6, "high": 0.9}
                topology_context["topology_score"] = score_map.get(fatigue_level, 0.5)

                if merged_biases:
                    dominant = max(set(b.get("type", "unknown") for b in merged_biases),
                                   key=lambda t: sum(1 for b in merged_biases if b.get("type") == t))
                    topology_context["bias_type"] = dominant

                if fatigue_level == "high":
                    topology_context["cluster_risk"] = "high"
                    topology_context["message"] = (
                        "High research fatigue detected — user may be experiencing decision degradation."
                    )
                    merged_alerts.append({
                        "code": "research_fatigue",
                        "level": "warning",
                        "message": "Research fatigue detected — consider taking a break.",
                    })
                elif fatigue_level == "medium":
                    topology_context["cluster_risk"] = "medium"
                    topology_context["message"] = "Moderate fatigue — monitor for continued escalation."
        else:
            # Fallback: simulate based on payload patterns
            patterns = payload.get("patterns", {})
            if patterns.get("chase_rally"):
                topology_context.update({
                    "cluster_risk": "high",
                    "bias_type": "momentum_bias",
                    "topology_score": 0.8,
                    "message": "User behavior aligns with 'Hype-Driven' cluster topology.",
                })
            elif patterns.get("overtrading"):
                topology_context.update({
                    "cluster_risk": "medium",
                    "bias_type": "activity_bias",
                    "topology_score": 0.6,
                    "message": "High-frequency activity detected in behavior topology.",
                })
    except Exception as e:
        logger.warning(f"enrich_psychology_with_topology failed for user {user_id}: {e}")

    payload["topology_context"] = topology_context
    payload["behavior_topology"] = {
        "fatigue_level": fatigue_level,
        "cognitive_biases": merged_biases,
        "alert_count": len(merged_alerts),
    }
    payload["alerts"] = merged_alerts

    # Set risk level based on topology
    if fatigue_level == "high" or topology_context["cluster_risk"] == "high":
        payload["risk_level"] = "elevated"
    elif fatigue_level == "medium":
        payload.setdefault("risk_level", "moderate")

    return payload
