from __future__ import annotations

"""Team blackboard — shared evidence notes with arbiter consensus."""

from typing import Any

from app.core.logger import get_logger

logger = get_logger(__name__)

_STANCE_FROM_STRENGTH = {
    "strong": 0.9,
    "moderate": 0.65,
    "weak": 0.4,
    "neutral": 0.5,
}


class TeamBlackboardService:
    """Persist and synthesize team-level evidence from members and agents."""

    def __init__(
        self,
        *,
        collaboration_repository: Any,
        debate_arbiter_service: Any | None = None,
        cross_team_meta_learning_service: Any | None = None,
        realtime_gateway_service: Any | None = None,
    ) -> None:
        self._repo = collaboration_repository
        self._arbiter = debate_arbiter_service
        self._cross_team = cross_team_meta_learning_service
        self._realtime = realtime_gateway_service

    def submit_note(
        self,
        *,
        team_id: int,
        user_id: int,
        evidence_key: str,
        evidence_value: str,
        agent_role: str = "member",
        symbol: str | None = None,
        strength: str = "moderate",
        narrative: str = "",
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        row = self._repo.add_blackboard_entry(
            team_id=team_id,
            user_id=user_id,
            agent_role=agent_role,
            evidence_key=evidence_key,
            evidence_value=evidence_value,
            symbol=symbol,
            strength=strength,
            narrative=narrative,
            payload=payload,
        )
        push_meta: dict[str, Any] | None = None
        if self._realtime is not None:
            try:
                push_meta = self._realtime.push_team_blackboard_entry(team_id, row)
            except Exception as exc:
                logger.debug("team blackboard socket push: %s", exc)
        return {"ok": True, "entry": row, "realtime": push_meta}

    def list_notes(
        self,
        team_id: int,
        *,
        symbol: str | None = None,
        limit: int = 80,
    ) -> dict[str, Any]:
        entries = self._repo.list_blackboard_entries(team_id, symbol=symbol, limit=limit)
        return {"ok": True, "team_id": team_id, "entries": entries, "count": len(entries)}

    def synthesize_consensus(
        self,
        team_id: int,
        *,
        symbol: str | None = None,
    ) -> dict[str, Any]:
        entries = self._repo.list_blackboard_entries(team_id, symbol=symbol, limit=100)
        if not entries:
            return {"ok": False, "status": "no_entries", "message": "团队黑板暂无证据"}

        bullish = bearish = neutral = 0.0
        for row in entries:
            key = str(row.get("evidence_key") or "").lower()
            val = str(row.get("evidence_value") or "").lower()
            w = _STANCE_FROM_STRENGTH.get(str(row.get("strength") or "moderate"), 0.5)
            text = f"{key} {val}"
            if any(k in text for k in ("bull", "buy", "利好", "看多")):
                bullish += w
            elif any(k in text for k in ("bear", "sell", "利空", "看空", "风险")):
                bearish += w
            else:
                neutral += w * 0.3

        total = bullish + bearish + neutral
        score = (bullish - bearish) / total if total else 0.0
        if score > 0.2:
            verdict = "bullish"
        elif score < -0.2:
            verdict = "bearish"
        else:
            verdict = "neutral"
        confidence = min(0.95, round(abs(score) + len(entries) * 0.03, 2))

        arbiter_extra: dict[str, Any] = {}
        if self._arbiter is not None and symbol:
            try:
                arbiter_extra = self._arbiter.synthesize(symbol, "CN", min_rounds=1)
            except Exception as exc:
                logger.debug("team blackboard arbiter: %s", exc)

        result = {
            "ok": True,
            "team_id": team_id,
            "symbol": symbol,
            "verdict": verdict,
            "confidence": confidence,
            "entries_used": len(entries),
            "stance_scores": {
                "bullish": round(bullish, 3),
                "bearish": round(bearish, 3),
                "neutral": round(neutral, 3),
            },
            "arbiter": arbiter_extra if arbiter_extra.get("ok") else None,
            "message": "团队黑板加权共识",
        }
        if self._cross_team is not None and symbol and verdict != "neutral":
            try:
                cross = self._cross_team.register_team_consensus(
                    team_id=team_id,
                    symbol=symbol,
                    market="CN",
                    verdict=verdict,
                    confidence=confidence,
                )
                if cross.get("site_alert") and cross["site_alert"].get("created"):
                    result["site_alert"] = cross["site_alert"]["alert"]
            except Exception as exc:
                logger.debug("team blackboard cross_team: %s", exc)
        if self._realtime is not None:
            try:
                result["realtime"] = self._realtime.push_team_blackboard_consensus(team_id, result)
            except Exception as exc:
                logger.debug("team blackboard consensus push: %s", exc)
        return result
