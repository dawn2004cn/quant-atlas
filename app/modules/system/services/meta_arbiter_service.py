from __future__ import annotations

"""Meta-Arbiter — site-level synthesis across independent team arbiters (8.0 P0)."""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from app.core.logger import get_logger
from app.core.mesh.memory_fabric import get_memory_fabric
from app.domain.meta_arbiter_schema import MetaArbiterVerdict, TeamSignalSummary
from app.infrastructure.collaboration.cross_team_store import CrossTeamStore

logger = get_logger(__name__)

_CONSENSUS_WINDOW_HOURS = 48
_MIN_CONFIDENCE = 0.6
_VERDICT_WEIGHTS = {
    "bullish": 1.0,
    "bearish": -1.0,
    "neutral": 0.0,
}
_CROSS_TEAM_BLEND = 0.65
_LOCAL_ARBITER_BLEND = 0.35


class MetaArbiterService:
    """Activate when ≥N teams agree — produce meta_verdict beyond passive alerts."""

    def __init__(
        self,
        *,
        cross_team_store: CrossTeamStore | None = None,
        swarm_arbiter_service: Any | None = None,
        min_teams: int = 3,
    ) -> None:
        self._store = cross_team_store or CrossTeamStore()
        self._arbiter = swarm_arbiter_service
        self._min_teams = max(2, min_teams)

    def synthesize(
        self,
        symbol: str,
        market: str = "CN",
        *,
        verdict_hint: str | None = None,
        use_llm: bool = False,
    ) -> dict[str, Any]:
        sym = (symbol or "").strip().lower()
        mkt = (market or "CN").strip().upper()
        if not sym:
            return {"ok": False, "error": "symbol_required"}

        signals = self._collect_team_signals(sym, mkt, verdict_hint=verdict_hint)
        if len(signals) < self._min_teams:
            return {
                "ok": False,
                "error": "insufficient_team_consensus",
                "team_count": len(signals),
                "min_teams": self._min_teams,
            }

        local = self._local_arbiter_consensus(sym, mkt, use_llm=use_llm)
        verdict = self._blend_verdict(signals, local)
        if use_llm:
            llm_note = self._llm_rationale(sym, mkt, signals, verdict)
            if llm_note:
                verdict["rationale"] = llm_note
                verdict["mode"] = verdict.get("mode", "") + "+llm"
        model = MetaArbiterVerdict(
            symbol=sym,
            market=mkt,
            meta_verdict=verdict["meta_verdict"],
            meta_confidence=verdict["meta_confidence"],
            team_count=len(signals),
            unanimous=verdict["unanimous"],
            dissent_teams=verdict["dissent_teams"],
            mode=verdict["mode"],
            rationale=verdict["rationale"],
            team_signals=signals,
            local_arbiter=local,
            activation_id=f"meta-{uuid.uuid4().hex[:12]}",
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        self._store.append_meta_verdict(model.model_dump())
        self._publish_activation(model)
        self._index_memory(model)
        logger.info(
            "MetaArbiter activated sym=%s verdict=%s teams=%d conf=%.2f",
            sym,
            model.meta_verdict,
            model.team_count,
            model.meta_confidence,
        )
        return {"ok": True, **model.model_dump()}

    def list_recent(self, *, limit: int = 30) -> dict[str, Any]:
        rows = self._store.list_meta_verdicts(limit=limit)
        return {"ok": True, "verdicts": rows, "count": len(rows)}

    def get_for_symbol(self, symbol: str, market: str = "CN") -> dict[str, Any]:
        sym = symbol.strip().lower()
        mkt = market.upper()
        for row in self._store.list_meta_verdicts(limit=100):
            if str(row.get("symbol") or "").lower() == sym and str(row.get("market") or "CN") == mkt:
                return {"ok": True, "verdict": row}
        return {"ok": False, "error": "meta_verdict_not_found"}

    def _collect_team_signals(
        self,
        symbol: str,
        market: str,
        *,
        verdict_hint: str | None,
    ) -> list[TeamSignalSummary]:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=_CONSENSUS_WINDOW_HOURS)
        rows = self._store.list_consensus(limit=1000)
        best_by_fp: dict[str, TeamSignalSummary] = {}
        hint = (verdict_hint or "").strip().lower()

        for row in rows:
            if str(row.get("symbol") or "").lower() != symbol:
                continue
            if str(row.get("market") or "").upper() != market:
                continue
            v = str(row.get("verdict") or "").lower()
            if hint and v != hint:
                continue
            conf = float(row.get("confidence") or 0.0)
            if conf < _MIN_CONFIDENCE:
                continue
            try:
                ts = datetime.fromisoformat(str(row.get("created_at") or "").replace("Z", "+00:00"))
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=timezone.utc)
            except ValueError:
                ts = datetime.now(timezone.utc)
            if ts < cutoff:
                continue
            fp = str(row.get("team_fp") or "")
            if not fp:
                continue
            age_hours = max(0.0, (datetime.now(timezone.utc) - ts).total_seconds() / 3600.0)
            recency = max(0.35, 1.0 - age_hours / _CONSENSUS_WINDOW_HOURS)
            weight = conf * recency
            existing = best_by_fp.get(fp)
            if existing is None or weight > existing.weight:
                best_by_fp[fp] = TeamSignalSummary(
                    team_fingerprint=fp,
                    verdict=v,
                    confidence=round(conf, 3),
                    weight=round(weight, 3),
                )
        return list(best_by_fp.values())

    def _local_arbiter_consensus(
        self,
        symbol: str,
        market: str,
        *,
        use_llm: bool,
    ) -> dict[str, Any] | None:
        if self._arbiter is None:
            return None
        try:
            sym = symbol.upper()
            return self._arbiter.consensus_only(sym, market, use_llm=use_llm)
        except Exception as exc:
            logger.warning("meta_arbiter local consensus sym=%s: %s", symbol, exc)
            return None

    def _blend_verdict(
        self,
        signals: list[TeamSignalSummary],
        local: dict[str, Any] | None,
    ) -> dict[str, Any]:
        score = 0.0
        total_w = 0.0
        verdict_counts: dict[str, int] = {}
        for sig in signals:
            w = sig.weight
            total_w += w
            score += _VERDICT_WEIGHTS.get(sig.verdict, 0.0) * w
            verdict_counts[sig.verdict] = verdict_counts.get(sig.verdict, 0) + 1

        cross_verdict = "neutral"
        if score > 0.15 * total_w:
            cross_verdict = "bullish"
        elif score < -0.15 * total_w:
            cross_verdict = "bearish"
        cross_conf = min(0.95, total_w / max(len(signals), 1))

        dominant = max(verdict_counts, key=verdict_counts.get)
        unanimous = len(verdict_counts) == 1
        dissent = len(signals) - verdict_counts.get(dominant, 0)

        meta_verdict = cross_verdict
        meta_conf = cross_conf
        mode = "weighted_cross_team"
        rationale = (
            f"{len(signals)} 个独立团队信号加权综合为 {cross_verdict}，"
            f"主导 verdict {dominant}（{'全票一致' if unanimous else f'分歧 {dissent} 队'}）。"
        )

        if local and local.get("ok"):
            local_v = str(local.get("verdict") or "neutral").lower()
            local_c = float(local.get("confidence") or 0.0)
            if local_v in _VERDICT_WEIGHTS:
                blended_score = (
                    _VERDICT_WEIGHTS[cross_verdict] * _CROSS_TEAM_BLEND * cross_conf
                    + _VERDICT_WEIGHTS[local_v] * _LOCAL_ARBITER_BLEND * local_c
                )
                if blended_score > 0.1:
                    meta_verdict = "bullish"
                elif blended_score < -0.1:
                    meta_verdict = "bearish"
                else:
                    meta_verdict = "neutral"
                meta_conf = min(
                    0.98,
                    cross_conf * _CROSS_TEAM_BLEND + local_c * _LOCAL_ARBITER_BLEND,
                )
                mode = "cross_team_plus_local_debate"
                llm_note = local.get("llm_rationale") or local.get("message") or ""
                if llm_note:
                    rationale += f" 本地辩论缓冲：{str(llm_note)[:160]}"
                elif local.get("rounds_used"):
                    rationale += f" 本地辩论 {local.get('rounds_used')} 轮参与融合。"

        return {
            "meta_verdict": meta_verdict,
            "meta_confidence": round(meta_conf, 3),
            "unanimous": unanimous,
            "dissent_teams": dissent,
            "mode": mode,
            "rationale": rationale,
        }

    def _llm_rationale(
        self,
        symbol: str,
        market: str,
        signals: list[TeamSignalSummary],
        verdict: dict[str, Any],
    ) -> str:
        try:
            from app.core.llm_config import get_llm

            llm = get_llm()
            summary = ", ".join(
                f"{s.team_fingerprint}:{s.verdict}@{s.confidence}" for s in signals[:8]
            )
            prompt = (
                f"标的 {symbol} ({market}) 跨团队元仲裁：{len(signals)} 个匿名团队信号 [{summary}]，"
                f"综合 verdict={verdict.get('meta_verdict')} conf={verdict.get('meta_confidence')}。"
                "请用一句中文说明全站级投资含义（不含具体团队身份，80字内）。"
            )
            response = llm.invoke(prompt)
            text = str(getattr(response, "content", response)).strip()
            return text[:200] if text else verdict.get("rationale", "")
        except Exception as exc:
            logger.debug("meta_arbiter llm rationale: %s", exc)
            return verdict.get("rationale", "")

    def _publish_activation(self, verdict: MetaArbiterVerdict) -> None:
        try:
            from app.core.event_bus import MetaArbiterActivatedEvent, get_event_bus

            get_event_bus().publish(
                MetaArbiterActivatedEvent(
                    source="MetaArbiterService",
                    activation_id=verdict.activation_id,
                    symbol=verdict.symbol,
                    market=verdict.market,
                    meta_verdict=verdict.meta_verdict,
                    meta_confidence=verdict.meta_confidence,
                    team_count=verdict.team_count,
                    unanimous=verdict.unanimous,
                    rationale=verdict.rationale[:500],
                )
            )
        except Exception as exc:
            logger.debug("meta_arbiter event publish: %s", exc)

    def _index_memory(self, verdict: MetaArbiterVerdict) -> None:
        try:
            fabric = get_memory_fabric()
            verdict_dict = verdict.model_dump()
            fabric.index_verdict(verdict_dict)
        except Exception as exc:
            logger.debug("memory fabric index: %s", exc)


__all__ = ["MetaArbiterService"]
