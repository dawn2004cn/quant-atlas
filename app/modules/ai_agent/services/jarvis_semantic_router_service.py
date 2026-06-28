from __future__ import annotations

"""Jarvis semantic penetration — fuzzy intents + UserKnowledge pattern matching (7.0)."""

import re
import uuid
from typing import Any
from urllib.parse import urlencode

from app.core.logger import get_logger
from app.core.middleware.health_aware import append_health_notice
from app.core.strategic_sunset import feature_enabled
from app.domain.dto.decision_context_dto import DecisionContextDTO, EvidenceNoteDTO
from app.modules.ai_agent.services.command_plan_service import CommandPlanService

logger = get_logger(__name__)

_WINNING_OUTCOMES = frozenset({"win", "profit", "success", "correct", "bullish", "positive"})

_PATTERN_INTENT_RE = re.compile(
    r"赚钱|成功模式|去年|前年|风格|偏好|适合我|像我.*赚|复盘.*赢|盈利模式",
    re.IGNORECASE,
)
_VOICE_RE = re.compile(r"语音|播报|晨间|播客|朗读|听.*简报|voice", re.IGNORECASE)
_WAR_ROOM_RE = re.compile(r"压力测试|war\s*room|黑天鹅|加息|反事实|模拟战", re.IGNORECASE)
_BRIEFING_RE = re.compile(r"日报|简报|smart.?daily|今日机会|晨间简报", re.IGNORECASE)


def _new_decision_id() -> str:
    return f"jarvis_{uuid.uuid4().hex[:12]}"


def _build_winning_pattern_risk_note(
    sectors: set[str], factors: set[str]
) -> EvidenceNoteDTO | None:
    """Generate a targeted risk notice based on winning pattern concentration."""
    if not sectors and not factors:
        return None
    warnings: list[str] = []
    if len(sectors) <= 2:
        top = ", ".join(sorted(sectors)[:2])
        warnings.append(f"Your winning patterns are concentrated in [{top}]. Consider diversification.")
    if "momentum" in {f.lower() for f in factors}:
        warnings.append("Momentum factor has historically mean-reverted — set trailing stops.")
    if "growth" in {f.lower() for f in factors}:
        warnings.append("Growth stocks are sensitive to rate changes — watch macro signals.")
    if "tech" in {s.lower() for s in sectors}:
        warnings.append("Tech sector concentration increases tail risk — hedge with defensive positions.")
    if not warnings:
        return None
    return EvidenceNoteDTO(
        source="persona_risk_notice",
        title="针对性风险提示",
        payload={"warnings": warnings[:3]},
    )


def _nav_dto(
    *,
    subject: str,
    intent: str,
    label: str,
    url: str,
    action: str = "navigate",
    reasoning: list[str] | None = None,
    evidence: list[EvidenceNoteDTO] | None = None,
    extra_snapshot: dict[str, Any] | None = None,
) -> DecisionContextDTO:
    snapshot: dict[str, Any] = {
        "ok": True,
        "intent": intent,
        "label": label,
        "url": url,
        "action": action,
    }
    if extra_snapshot:
        snapshot.update(extra_snapshot)
    return append_health_notice(
        DecisionContextDTO(
            decision_id=_new_decision_id(),
            subject=subject,
            model_version="jarvis_semantic_router_v1",
            input_snapshot=snapshot,
            reasoning_trace=reasoning or [f"Jarvis heuristic routing: {label}"],
            evidence=evidence or [],
        )
    )


class JarvisSemanticRouterService:
    """Route natural language to actionable URLs with knowledge-aware stock picks."""

    def __init__(
        self,
        *,
        user_knowledge_service: Any | None = None,
        strategy_service: Any | None = None,
        command_plan_service: CommandPlanService | None = None,
    ) -> None:
        self._knowledge = user_knowledge_service
        self._strategy = strategy_service
        self._plan = command_plan_service or CommandPlanService()

    def route(self, user_id: int | str, query: str) -> DecisionContextDTO:
        text = (query or "").strip()
        if not text:
            return append_health_notice(
                DecisionContextDTO(
                    decision_id=_new_decision_id(),
                    subject=f"user:{user_id}",
                    model_version="jarvis_semantic_router_v1",
                    input_snapshot={"ok": False, "error": "query_required"},
                    reasoning_trace=["Empty query — routing aborted"],
                )
            )

        if _VOICE_RE.search(text):
            return self._enrich_dto_with_persona(self._voice_briefing_route(text), user_id, text)
        if _WAR_ROOM_RE.search(text) and feature_enabled("war_room"):
            return _nav_dto(
                subject=text,
                intent="war_room",
                label="打开 War Room 反事实模拟战",
                url="/war-room",
                reasoning=["Matched War Room intent"],
            )
        if _BRIEFING_RE.search(text):
            return _nav_dto(
                subject=text,
                intent="smart_briefing",
                label="打开叙事语音简报",
                url="/voice-briefing",
                reasoning=["Matched smart daily briefing intent"],
            )
        if _PATTERN_INTENT_RE.search(text):
            return self._pattern_stock_route(user_id, text)

        plan = self._plan.build_semantic_plan(text, user_id=user_id, knowledge=self._knowledge)
        if plan.get("intent") not in {None, "direct_command", "conditional_automation"}:
            return _nav_dto(
                subject=text,
                intent=str(plan.get("intent")),
                label=plan.get("label") or "执行 Jarvis 语义指令",
                url=plan.get("url") or "/market-panorama",
                reasoning=[f"CommandPlanService returned intent={plan.get('intent')}"],
                extra_snapshot={"semantic_plan": plan},
            )

        return self._enrich_dto_with_persona(self._heuristic_nav(text), user_id, text)

    def match_winning_patterns(self, user_id: int | str) -> DecisionContextDTO:
        if self._knowledge is None:
            return DecisionContextDTO(
                decision_id=_new_decision_id(),
                subject=f"winning_patterns:{user_id}",
                model_version="jarvis_semantic_router_v1",
                input_snapshot={"ok": False, "error": "user_knowledge_unavailable"},
                reasoning_trace=["User knowledge service not configured"],
            )
        profile = self._knowledge.get_profile(user_id)
        patterns = [
            p
            for p in profile.get("decision_patterns") or []
            if str(p.get("outcome") or "").lower() in _WINNING_OUTCOMES
        ]
        sectors: dict[str, int] = {}
        factors: dict[str, int] = {}
        symbols: dict[str, int] = {}
        for pat in patterns:
            for sec in pat.get("sectors") or []:
                key = str(sec).strip()
                if key:
                    sectors[key] = sectors.get(key, 0) + 1
            for fac in pat.get("factors") or []:
                key = str(fac).strip()
                if key:
                    factors[key] = factors.get(key, 0) + 1
            for sym in pat.get("symbols") or []:
                key = str(sym).strip().lower()
                if key:
                    symbols[key] = symbols.get(key, 0) + 1

        top_sectors = sorted(sectors, key=sectors.get, reverse=True)[:5]
        top_factors = sorted(factors, key=factors.get, reverse=True)[:5]
        top_symbols = sorted(symbols, key=symbols.get, reverse=True)[:10]
        return DecisionContextDTO(
            decision_id=_new_decision_id(),
            subject=f"winning_patterns:{user_id}",
            model_version="jarvis_semantic_router_v1",
            input_snapshot={
                "ok": True,
                "pattern_count": len(patterns),
                "top_sectors": top_sectors,
                "top_factors": top_factors,
                "top_symbols": top_symbols,
                "recent_wins": patterns[-5:],
            },
            reasoning_trace=[f"Aggregated {len(patterns)} winning decision patterns"],
            evidence=[
                EvidenceNoteDTO(
                    source="user_knowledge",
                    title=f"{len(patterns)} winning patterns",
                    payload={"top_sectors": top_sectors, "top_factors": top_factors},
                )
            ],
        )

    def _enrich_dto_with_persona(
        self, dto: DecisionContextDTO, user_id: int | str, query: str
    ) -> DecisionContextDTO:
        """Attach persona-aware evidence (winning patterns) to a navigation DTO."""
        if self._knowledge is None:
            return dto
        try:
            profile = self._knowledge.get_profile(user_id)
            patterns = [
                p
                for p in profile.get("decision_patterns") or []
                if str(p.get("outcome") or "").lower() in _WINNING_OUTCOMES
            ]
            if not patterns:
                return dto

            sectors = set()
            factors = set()
            for pat in patterns:
                for sec in pat.get("sectors") or []:
                    if str(sec).strip():
                        sectors.add(str(sec).strip())
                for fac in pat.get("factors") or []:
                    if str(fac).strip():
                        factors.add(str(fac).strip())

            note = EvidenceNoteDTO(
                source="persona_aware",
                title="Your Winning Style",
                payload={
                    "sectors": sorted(sectors)[:5],
                    "factors": sorted(factors)[:5],
                    "pattern_count": len(patterns),
                    "tip": "Focus on your historically profitable sectors and factors.",
                },
            )

            risk_note = _build_winning_pattern_risk_note(sectors, factors)

            existing = dto.evidence or []
            evidence = existing + [note]
            if risk_note is not None:
                evidence.append(risk_note)

            return DecisionContextDTO(
                decision_id=dto.decision_id,
                subject=dto.subject,
                model_version=dto.model_version,
                input_snapshot=dto.input_snapshot,
                reasoning_trace=dto.reasoning_trace + ["Enriched with persona-aware evidence"],
                evidence=evidence,
            )
        except Exception:
            return dto

    def _pattern_stock_route(self, user_id: int | str, query: str) -> DecisionContextDTO:
        ctx = self.match_winning_patterns(user_id)
        snapshot = ctx.input_snapshot
        if not snapshot.get("ok"):
            return _nav_dto(
                subject=query,
                intent="pattern_stock_pick",
                label="暂未记录您的成功交易模式，请先积累决策复盘",
                url="/self-stocks",
                reasoning=["No winning patterns recorded for user"],
            )

        candidates = self._pick_candidates(snapshot)
        sectors = snapshot.get("top_sectors") or []
        factors = snapshot.get("top_factors") or []
        label_parts = ["匹配您的历史赚钱风格"]
        if sectors:
            label_parts.append("板块 " + "、".join(sectors[:3]))
        if factors:
            label_parts.append("因子 " + "、".join(factors[:2]))
        label = " · ".join(label_parts)
        if candidates:
            label += f" · {len(candidates)} 只候选"

        params: dict[str, str] = {"jarvis": "winning_style"}
        if sectors:
            params["sectors"] = ",".join(sectors[:3])
        if candidates:
            params["symbols"] = ",".join(
                str(c.get("symbol") or c.get("code") or "") for c in candidates[:5]
            )
        url = "/market-panorama?" + urlencode({k: v for k, v in params.items() if v})

        return _nav_dto(
            subject=query,
            intent="pattern_stock_pick",
            label=label,
            url=url,
            reasoning=[f"Pattern-based stock pick for user {user_id}"],
            extra_snapshot={
                "pattern_context": snapshot,
                "candidates": candidates,
            },
            evidence=[
                EvidenceNoteDTO(
                    source="pattern_match",
                    title=f"Matched sectors: {sectors[:3]}",
                    payload={"sectors": sectors, "factors": factors},
                )
            ],
        )

    def _pick_candidates(self, ctx: dict[str, Any]) -> list[dict[str, Any]]:
        if self._strategy is None:
            return [
                {"symbol": sym, "name": sym, "match_reason": "historical_win_symbol"}
                for sym in (ctx.get("top_symbols") or [])[:5]
            ]
        try:
            from app.domain.enums import MarketCode

            result = self._strategy.select_stocks(
                strategy_name="smart",
                market=MarketCode.CN,
                top_n=12,
            )
            if not result.get("ok"):
                raise ValueError(result.get("error") or "select_failed")
            pool = result.get("candidates") or []
            sectors = set(ctx.get("top_sectors") or [])
            factors = set(ctx.get("top_factors") or [])
            scored: list[tuple[float, dict[str, Any]]] = []
            for row in pool:
                score = 0.0
                sec = str(row.get("sector") or row.get("industry") or "")
                if sec and any(s in sec for s in sectors):
                    score += 2.0
                strat = str(row.get("strategy") or row.get("category") or "").lower()
                if any(f.lower() in strat for f in factors):
                    score += 1.5
                sym = str(row.get("symbol") or row.get("code") or "").lower()
                if sym in (ctx.get("top_symbols") or []):
                    score += 1.0
                if score > 0:
                    item = dict(row)
                    item["match_score"] = round(score, 2)
                    item["match_reason"] = "winning_style_alignment"
                    scored.append((score, item))
            scored.sort(key=lambda x: x[0], reverse=True)
            if scored:
                return [item for _, item in scored[:5]]
        except Exception as exc:
            logger.warning("pattern pick via strategy failed: %s", exc)

        return [
            {"symbol": sym, "name": sym, "match_reason": "historical_win_symbol"}
            for sym in (ctx.get("top_symbols") or [])[:5]
        ]

    @staticmethod
    def _voice_briefing_route(query: str) -> DecisionContextDTO:
        _ = query
        return _nav_dto(
            subject=query,
            intent="voice_briefing",
            label="打开叙事语音简报（晨间播客）",
            url="/voice-briefing",
            reasoning=["Matched voice briefing intent"],
        )

    @staticmethod
    def _heuristic_nav(text: str) -> DecisionContextDTO:
        q = text.strip()
        code_match = re.search(r"\b(\d{6})\b", q)
        if code_match and ("分析" in q or "看看" in q):
            sym = code_match.group(1)
            return _nav_dto(
                subject=text,
                intent="analyze",
                label=f"分析 {sym}",
                url=f"/stock/{sym}?m=CN",
                reasoning=["Heuristic: 6-digit stock code detected in query"],
            )
        if "回测" in q:
            return _nav_dto(
                subject=text,
                intent="backtest",
                label="前往策略回测实验室",
                url="/backtest",
                reasoning=["Heuristic: backtest keyword detected"],
            )
        if "自选" in q:
            return _nav_dto(
                subject=text,
                intent="watchlist",
                label="管理自选股",
                url="/self-stocks",
                reasoning=["Heuristic: watchlist keyword detected"],
            )
        if feature_enabled("swarm_topology") and ("swarm" in q.lower() or "拓扑" in q):
            return _nav_dto(
                subject=text,
                intent="swarm_designer",
                label="打开 Swarm Designer",
                url="/swarm-designer",
                reasoning=["Heuristic: swarm designer keyword detected"],
            )
        if "协作" in q or "黑板" in q:
            return _nav_dto(
                subject=text,
                intent="collaboration",
                label="打开协作投研工作区",
                url="/collaboration",
                reasoning=["Heuristic: collaboration keyword detected"],
            )
        return _nav_dto(
            subject=text,
            intent="search",
            label=f"在市场中搜索「{q}」",
            url=f"/market-panorama?filter={q}",
            reasoning=["Fallback heuristic: generic market search"],
        )


__all__ = ["JarvisSemanticRouterService"]
