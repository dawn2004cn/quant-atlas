from __future__ import annotations
"""Deep Replay — 证据时间轴回溯与 What-if 假设分析。"""

from datetime import datetime, timedelta, timezone
from typing import Any

from app.agents.research.debate_bus import get_recent_debate_rounds
from app.core.event_bus import get_event_bus
from app.core.logger import get_logger
from app.domain.enums import MarketCode
from app.infrastructure.replay.evidence_replay_store import list_snapshots

logger = get_logger(__name__)

_REPLAY_EVENT_TYPES = frozenset({
    "DebateRoundEvent",
    "TruthDeviationEvent",
    "AnalysisStaleEvent",
    "WorkflowCompletedEvent",
    "CapabilityExecutedEvent",
})


class EvidenceReplayService:
    """Build replay timelines and run counterfactual hypothesis checks."""

    def __init__(self, *, ai_evidence_service: Any | None = None) -> None:
        self._ai_evidence = ai_evidence_service

    def build_timeline(
        self,
        symbol: str,
        *,
        market: str = "CN",
        minutes_back: int = 120,
    ) -> dict[str, Any]:
        sym = symbol.strip().upper()
        mkt = market.upper()
        stored = list_snapshots(sym, mkt, minutes_back=minutes_back)
        bus_items = self._bus_events(sym, mkt, minutes_back=minutes_back)
        debate = get_recent_debate_rounds(sym, mkt, limit=40)
        merged = self._merge_timeline(stored, bus_items, debate)
        return {
            "symbol": sym,
            "market": mkt,
            "minutes_back": minutes_back,
            "node_count": len(merged),
            "nodes": merged,
        }

    def replay_at(
        self,
        symbol: str,
        *,
        market: str = "CN",
        minutes_ago: int = 60,
    ) -> dict[str, Any]:
        timeline = self.build_timeline(symbol, market=market, minutes_back=max(120, minutes_ago + 30))
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=max(0, minutes_ago))
        nodes = []
        for node in timeline["nodes"]:
            ts = self._parse_ts(node.get("timestamp"))
            if ts and ts <= cutoff:
                nodes.append(node)
        last = nodes[-1] if nodes else None
        return {
            "symbol": symbol.upper(),
            "market": market.upper(),
            "minutes_ago": minutes_ago,
            "replay_cutoff": cutoff.isoformat().replace("+00:00", "Z"),
            "nodes_at_cutoff": nodes,
            "conclusion_snapshot": last,
        }

    def what_if(
        self,
        symbol: str,
        *,
        market: str = "CN",
        user_hypothesis: str,
        minutes_ago: int = 0,
    ) -> dict[str, Any]:
        if not self._ai_evidence:
            return {"ok": False, "error": "ai_evidence_service_unavailable"}
        replay = self.replay_at(symbol, market=market, minutes_ago=minutes_ago)
        mkt = MarketCode.CN
        try:
            mkt = MarketCode(market.upper())
        except ValueError:
            logger.warning("Suppressed exception", exc_info=True)
            pass
        bundle = self._ai_evidence.build_bundle(
            symbol=symbol,
            market=mkt,
            user_hypothesis=user_hypothesis,
        )
        return {
            "ok": True,
            "symbol": symbol.upper(),
            "market": market.upper(),
            "minutes_ago": minutes_ago,
            "replay_context": replay,
            "what_if_bundle": bundle,
        }

    def _bus_events(self, symbol: str, market: str, *, minutes_back: int) -> list[dict[str, Any]]:
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=minutes_back)
        out: list[dict[str, Any]] = []
        for row in get_event_bus().list_recent_events(limit=200):
            if row.get("event") not in _REPLAY_EVENT_TYPES:
                continue
            data = row.get("data") or {}
            esym = str(data.get("symbol") or "").upper()
            if esym and esym != symbol:
                continue
            ts = self._parse_ts(row.get("timestamp"))
            if ts and ts < cutoff:
                continue
            out.append({
                "timestamp": row.get("timestamp"),
                "event_type": row.get("event"),
                "source": row.get("source") or "event_bus",
                "summary": self._summarize_event(row),
                "payload": data,
                "priority": row.get("priority"),
            })
        return out

    @staticmethod
    def _merge_timeline(
        stored: list[dict[str, Any]],
        bus: list[dict[str, Any]],
        debate: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        nodes: list[dict[str, Any]] = []
        for row in stored:
            nodes.append({
                "timestamp": row.get("timestamp"),
                "event_type": row.get("event_type"),
                "source": row.get("source") or "replay_store",
                "summary": str((row.get("payload") or {}).get("evidence_summary") or row.get("event_type")),
                "payload": row.get("payload") or {},
            })
        nodes.extend(bus)
        for d in debate:
            nodes.append({
                "timestamp": d.get("timestamp"),
                "event_type": "DebateRoundEvent",
                "source": "debate_bus",
                "summary": f"{d.get('agent_role')} · {d.get('stance')} R{d.get('round_num')}",
                "payload": d,
            })
        nodes.sort(key=lambda n: str(n.get("timestamp") or ""))
        return nodes

    @staticmethod
    def _summarize_event(row: dict[str, Any]) -> str:
        name = row.get("event") or "event"
        data = row.get("data") or {}
        if name == "TruthDeviationEvent":
            return f"数据偏差 {data.get('diff_pct')}% ({data.get('source_a')} vs {data.get('source_b')})"
        if name == "DebateRoundEvent":
            return f"{data.get('agent_role')} {data.get('stance')} conf={data.get('confidence')}"
        return name

    @staticmethod
    def _parse_ts(raw: Any) -> datetime | None:
        if not raw:
            return None
        try:
            dt = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except ValueError:
            return None
