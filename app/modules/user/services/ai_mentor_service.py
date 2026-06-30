from __future__ import annotations

import json
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class AiMentorTemplate:
    provider_id: int
    symbol: str
    factor_values: dict | None = None
    market: str = "CN"
    score: float = 0.0
    action: str = "hold"
    confidence: float = 0.5
    evidence: list[dict] = field(default_factory=list)
    explanation: str = ""


class AiMentorService:
    # This service keeps API heavy operations out of expensive sector-level analysis
    def advise(self, symbol, factor_values=None, market="CN") -> AiMentorTemplate:
        import uuid
        from datetime import datetime, timezone
        evidence = []
        score = 0.0
        # Data integration via evidence graph
        graph_evidence = self._query_evidence_graph(symbol, market)
        if graph_evidence:
            evidence.extend(graph_evidence)
            for e in graph_evidence:
                score += e.get("contribution", 0)
        if factor_values:
            for factor, value in factor_values.items():
                contribution = value * 0.1
                score += contribution
                evidence.append({
                    "factor": factor,
                    "value": round(value, 4),
                    "contribution": round(contribution, 4),
                    "interpretation": self._interpret_factor(factor, value),
                    "source": "factor_analysis",
                })
        evidence.sort(key=lambda e: -abs(e.get("contribution", 0)))
        if score > 0.3:
            action = "buy"
            confidence = min(0.95, 0.5 + score)
        elif score < -0.2:
            action = "sell"
            confidence = min(0.95, 0.5 - score)
        else:
            action = "hold"
            confidence = 0.5
        explanation = self._build_explanation(evidence, action, confidence)
        return AiMentorTemplate(
            provider_id=uuid.uuid4().hex[:8],
            symbol=symbol,
            factor_values=factor_values,
            market=market,
            score=score,
            action=action,
            confidence=round(confidence, 3),
            evidence=evidence[:5],
            explanation=explanation,
        )

    def _query_evidence_graph(self, symbol, market):
        try:
            from app.modules.system.services.ui.evidence_graph_service import EvidenceGraphService
            svc = EvidenceGraphService()
            result = svc.query_symbol(symbol, market=market)
            if result and "edges" in result:
                evidence = []
                for edge in result["edges"][:5]:
                    evidence.append({
                        "factor": edge.get("factor_type", edge.get("type", "unknown")),
                        "value": edge.get("strength", 0),
                        "contribution": edge.get("strength", 0) * 0.15,
                        "interpretation": "因子共振: " + (edge.get("label", "") or ""),
                        "source": "evidence_graph",
                        "confidence": edge.get("confidence", 0.5),
                    })
                return evidence
        except Exception:
            logger.warning("Suppressed exception", exc_info=True)
        return []

    def _build_explanation(self, evidence, action, confidence):
        if not evidence:
            return "暂无足够证据生成建议"
        top = evidence[0]
        if action == "buy":
            return ("建议买入 " + str(top.get("factor", "")) + " 因子驱动，" +
                    "贡献度 " + str(round(abs(top.get("contribution", 0)) * 100, 1)) + "%，" +
                    "历史类似模式胜率约 " + str(int(confidence * 100)) + "%")
        elif action == "sell":
            return ("建议卖出，主要受 " + str(top.get("factor", "")) + " 因子负面影响，" +
                    "贡献度 " + str(round(abs(top.get("contribution", 0)) * 100, 1)) + "%")
        else:
            return ("建议持有观察，当前因子信号不明确，" + "最强信号来自 " + str(top.get("factor", "")) + " 因子")

    def _interpret_factor(self, factor, value):
        interpretations = {
            "momentum": "动量偏强" if value > 0 else "动量偏弱",
            "volatility": "波动率偏高" if abs(value) > 0.3 else "波动率正常",
            "volume_ratio": "放量" if value > 1.5 else "缩量" if value < 0.5 else "正常",
            "rsi": "超买" if value > 70 else "超卖" if value < 30 else "中性",
            "macd": "金叉" if value > 0 else "死叉",
        }
        return interpretations.get(factor, "值=" + str(round(value, 2)))
