from __future__ import annotations
"""Synthesize multi-round debate consensus from EventBus buffer."""

from typing import Any

from app.agents.research.debate_bus import get_recent_debate_rounds
from app.core.logger import get_logger
from app.domain.dto.service_result import GenericResponseDTO

logger = get_logger(__name__)

_MIN_CONFIDENCE = 0.35
_STANCE_WEIGHTS = {
    "bullish": 1.0,
    "bearish": -1.0,
    "risk_seeking": 0.35,
    "risk_averse": -0.35,
    "neutral": 0.0,
}


class DebateArbiterService:
    """Collect debate rounds and produce a weighted consensus verdict."""

    def __init__(
        self,
        *,
        correction_intent_service: Any | None = None,
        sequence_chain_service: Any | None = None,
        review_learning_service: Any | None = None,
    ) -> None:
        self._correction = correction_intent_service
        self._sequence = sequence_chain_service
        self._learning = review_learning_service

    def synthesize(
        self,
        symbol: str,
        market: str = "CN",
        *,
        min_rounds: int = 2,
        use_llm: bool = False,
    ) -> GenericResponseDTO:
        if use_llm:
            return self.synthesize_with_llm(symbol, market, min_rounds=min_rounds)
        base = self._build_heuristic_consensus(symbol, market, min_rounds=min_rounds)
        if not base.get("ok"):
            return base
        return self._finalize_consensus(base, symbol, market)

    def synthesize_with_llm(
        self,
        symbol: str,
        market: str = "CN",
        *,
        min_rounds: int = 2,
    ) -> GenericResponseDTO:
        """LLM synthesis with heuristic fallback."""
        base = self._build_heuristic_consensus(symbol, market, min_rounds=min_rounds)
        rounds = base.get("recent_rounds") or []
        if len(rounds) < min_rounds:
            base["mode"] = "heuristic"
            return base

        try:
            from app.core.llm_config import get_llm

            llm = get_llm()
            excerpts = "\n".join(
                f"- [{r.get('agent_role')}] {r.get('stance')} (conf={r.get('confidence')}): "
                f"{(r.get('evidence_summary') or '')[:200]}"
                for r in rounds[-8:]
            )
            prompt = (
                f"标的 {symbol} ({market}) 多智能体辩论摘录：\n{excerpts}\n\n"
                "请综合多空证据，剔除自相矛盾且低置信观点，输出 JSON："
                '{"verdict":"bullish|bearish|neutral","confidence":0.0-1.0,"rationale":"..."}'
            )
            response = llm.invoke(prompt)
            text = getattr(response, "content", str(response))
            parsed = self._parse_llm_verdict(str(text))
            if parsed:
                return self._finalize_consensus(
                    {
                        **base,
                        "ok": True,
                        "status": "consensus_ready",
                        "verdict": parsed.get("verdict", base.get("verdict")),
                        "confidence": float(
                            parsed.get("confidence", base.get("confidence", 0.5))
                        ),
                        "llm_rationale": parsed.get("rationale", ""),
                        "mode": "llm",
                        "message": "LLM 仲裁综合（含启发式回退）",
                    },
                    symbol,
                    market,
                )
        except Exception as exc:  # noqa: BLE001
            logger.warning("DebateArbiter LLM synthesis failed: %s", exc)

        base["mode"] = "heuristic"
        base["llm_rationale"] = None
        return self._finalize_consensus(base, symbol, market)

    def _finalize_consensus(
        self,
        result: GenericResponseDTO,
        symbol: str,
        market: str,
    ) -> GenericResponseDTO:
        """Publish ArbiterConsensusEvent and optional CorrectionIntent."""
        if not result.get("ok"):
            return result
        from app.core.event_bus import ArbiterConsensusEvent, get_event_bus
        from app.domain.sequence_chain import new_provenance_id

        provenance_id = None
        if self._sequence is not None:
            provenance_id = self._sequence.get_active_provenance(symbol, market)
        if not provenance_id:
            provenance_id = new_provenance_id()
        result["provenance_id"] = provenance_id

        get_event_bus().publish(
            ArbiterConsensusEvent(
                source="DebateArbiterService",
                provenance_id=provenance_id,
                symbol=symbol.strip().lower(),
                market=market.upper(),
                verdict=str(result.get("verdict") or "neutral"),
                confidence=float(result.get("confidence") or 0.0),
                mode=str(result.get("mode") or "heuristic"),
                rounds_used=int(result.get("rounds_used") or 0),
            )
        )

        if self._correction is not None:
            intent = self._correction.maybe_emit_correction(
                provenance_id=provenance_id,
                symbol=symbol,
                market=market,
                verdict=str(result.get("verdict") or ""),
                confidence=float(result.get("confidence") or 0.0),
            )
            if intent is not None:
                result["correction_intent"] = intent.model_dump()
        return result

    def _build_heuristic_consensus(
        self,
        symbol: str,
        market: str,
        *,
        min_rounds: int = 2,
    ) -> GenericResponseDTO:
        rounds = get_recent_debate_rounds(
            symbol,
            market,
            limit=40,
            min_confidence=_MIN_CONFIDENCE,
        )
        excluded = get_recent_debate_rounds(symbol, market, limit=40, min_confidence=0.0)
        excluded_count = len(excluded) - len(rounds)

        if len(rounds) < min_rounds:
            return {
                "ok": False,
                "symbol": symbol.upper(),
                "market": market.upper(),
                "status": "insufficient_rounds",
                "rounds_used": len(rounds),
                "rounds_excluded": excluded_count,
                "verdict": "neutral",
                "confidence": 0.0,
                "recent_rounds": rounds[-6:],
                "message": f"需要至少 {min_rounds} 轮高置信辩论，当前 {len(rounds)} 轮",
            }

        score = 0.0
        weight_sum = 0.0
        by_stance: dict[str, int] = {}
        weights = (
            self._learning.get_stance_weights()
            if self._learning is not None
            else _STANCE_WEIGHTS
        )
        for row in rounds:
            stance = str(row.get("stance") or "neutral")
            conf = float(row.get("confidence") or 0.5)
            w = weights.get(stance, 0.0) * conf
            score += w
            weight_sum += abs(conf)
            by_stance[stance] = by_stance.get(stance, 0) + 1

        normalized = score / weight_sum if weight_sum else 0.0
        if normalized > 0.25:
            verdict = "bullish"
        elif normalized < -0.25:
            verdict = "bearish"
        else:
            verdict = "neutral"

        consensus_conf = min(0.95, round(abs(normalized) + len(rounds) * 0.05, 2))
        return {
            "ok": True,
            "symbol": symbol.upper(),
            "market": market.upper(),
            "status": "consensus_ready",
            "verdict": verdict,
            "score": round(normalized, 4),
            "confidence": consensus_conf,
            "rounds_used": len(rounds),
            "rounds_excluded": excluded_count,
            "stance_counts": by_stance,
            "recent_rounds": rounds[-6:],
            "message": "基于 EventBus 辩论轮次加权共识",
            "mode": "heuristic",
        }

    @staticmethod
    def _parse_llm_verdict(text: str) -> dict[str, Any] | None:
        import json
        import re

        match = re.search(r"\{[^{}]*verdict[^{}]*\}", text, re.IGNORECASE | re.DOTALL)
        if not match:
            return None
        try:
            data = json.loads(match.group(0))
        except json.JSONDecodeError:
            return None
        verdict = str(data.get("verdict") or "").lower()
        if verdict not in ("bullish", "bearish", "neutral"):
            return None
        return {
            "verdict": verdict,
            "confidence": data.get("confidence"),
            "rationale": data.get("rationale"),
        }
