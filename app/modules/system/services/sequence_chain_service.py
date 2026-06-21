from __future__ import annotations
"""SequenceChainService — EventBus subscriber building evidence-trade lineage."""

from datetime import datetime
from typing import Any
from uuid import uuid4

from app.core.event_bus import (
    ArbiterConsensusEvent,
    CapabilityExecutedEvent,
    CorrectionIntentEvent,
    DebateRoundEvent,
    Event,
    TradeExecutedEvent,
    WorkflowCompletedEvent,
    get_event_bus,
)
from app.core.logger import get_logger
from app.domain.sequence_chain import SequenceChain, SequenceStep, new_provenance_id
from app.infrastructure.replay.sequence_chain_store import SequenceChainStore

logger = get_logger(__name__)

_started = False


class SequenceChainService:
    """Maintain causal chains across debate → consensus → trade events."""

    def __init__(self, store: SequenceChainStore | None = None) -> None:
        from app.config import BASE_DIR

        self._store = store or SequenceChainStore(BASE_DIR / "instance" / "sequence_chains")
        self._active: dict[str, SequenceChain] = {}
        self._by_id: dict[str, SequenceChain] = {}
        self._scope: dict[str, Any] = {
            "visibility": "private",
            "team_id": None,
            "owner_user_id": None,
        }

    def set_scope(
        self,
        *,
        visibility: str = "private",
        team_id: int | None = None,
        owner_user_id: int | None = None,
    ) -> None:
        """Configure provenance visibility for subsequent chains."""
        self._scope = {
            "visibility": visibility if visibility in ("private", "team", "public") else "private",
            "team_id": team_id,
            "owner_user_id": owner_user_id,
        }

    def start(self) -> None:
        """Subscribe to EventBus (idempotent)."""
        global _started
        if _started:
            return
        bus = get_event_bus()
        bus.subscribe(DebateRoundEvent, self._on_debate_round, priority=40)
        bus.subscribe(WorkflowCompletedEvent, self._on_workflow, priority=30)
        bus.subscribe(CapabilityExecutedEvent, self._on_capability, priority=20)
        bus.subscribe(ArbiterConsensusEvent, self._on_consensus, priority=50)
        bus.subscribe(CorrectionIntentEvent, self._on_correction_intent, priority=45)
        bus.subscribe(TradeExecutedEvent, self._on_trade, priority=60)
        _started = True
        logger.info("SequenceChainService started")

    def get_active_provenance(self, symbol: str, market: str = "CN") -> str | None:
        key = self._symbol_key(symbol, market)
        chain = self._active.get(key)
        return chain.provenance_id if chain else None

    def get_chain(self, provenance_id: str) -> SequenceChain | None:
        if provenance_id in self._by_id:
            return self._by_id[provenance_id]
        loaded = self._store.load_by_id(provenance_id)
        if loaded:
            self._by_id[provenance_id] = loaded
        return loaded

    def list_chains(
        self,
        *,
        symbol: str | None = None,
        team_id: int | None = None,
        visibility: str | None = None,
        limit: int = 50,
    ) -> list[SequenceChain]:
        mem = list(self._by_id.values())
        if symbol:
            sym = symbol.strip().lower()
            mem = [c for c in mem if c.symbol.lower() == sym]
        if team_id is not None:
            mem = [
                c
                for c in mem
                if c.team_id == team_id or c.visibility == "public"
            ]
        if visibility:
            mem = [c for c in mem if c.visibility == visibility]
        mem.sort(key=lambda c: c.updated_at, reverse=True)
        if len(mem) >= limit:
            return mem[:limit]
        disk = self._store.load_recent(
            symbol=symbol, team_id=team_id, visibility=visibility, limit=limit
        )
        seen = {c.provenance_id for c in mem}
        for chain in disk:
            if chain.provenance_id not in seen:
                mem.append(chain)
                seen.add(chain.provenance_id)
        mem.sort(key=lambda c: c.updated_at, reverse=True)
        return mem[:limit]

    def append_manual_step(
        self,
        provenance_id: str,
        *,
        event_type: str,
        label: str,
        payload: dict[str, Any] | None = None,
    ) -> SequenceChain | None:
        chain = self.get_chain(provenance_id)
        if chain is None:
            return None
        self._append_step(chain, event_type, label, payload or {})
        return chain

    def _on_debate_round(self, event: Event) -> None:
        if not isinstance(event, DebateRoundEvent):
            return
        chain = self._ensure_active_chain(event.symbol, event.market, "DebateRoundEvent")
        self._append_step(
            chain,
            "DebateRoundEvent",
            f"{event.agent_role} · {event.stance}",
            {
                "round_num": event.round_num,
                "agent_role": event.agent_role,
                "stance": event.stance,
                "confidence": event.confidence,
                "evidence_summary": (event.evidence_summary or "")[:300],
            },
        )

    def _on_workflow(self, event: Event) -> None:
        if not isinstance(event, WorkflowCompletedEvent):
            return
        sym = str(getattr(event, "symbol", "") or "")
        market = str(getattr(event, "market", "CN") or "CN")
        if not sym:
            return
        chain = self._ensure_active_chain(sym, market, "WorkflowCompletedEvent")
        self._append_step(
            chain,
            "WorkflowCompletedEvent",
            event.workflow_type or "workflow",
            {
                "workflow_id": event.workflow_id,
                "state": event.state,
                "evidence_count": event.evidence_count,
            },
        )

    def _on_capability(self, event: Event) -> None:
        if not isinstance(event, CapabilityExecutedEvent):
            return
        sym = str(getattr(event, "symbol", "") or "")
        if not sym:
            return
        market = str(getattr(event, "market", "CN") or "CN")
        chain = self._ensure_active_chain(sym, market, "CapabilityExecutedEvent")
        self._append_step(
            chain,
            "CapabilityExecutedEvent",
            event.capability_name,
            {"success": event.success, "duration_ms": event.duration_ms},
        )

    def _on_consensus(self, event: Event) -> None:
        if not isinstance(event, ArbiterConsensusEvent):
            return
        chain = self._resolve_chain(event.provenance_id, event.symbol, event.market)
        if chain is None:
            return
        chain.status = "consensus"
        self._append_step(
            chain,
            "ArbiterConsensusEvent",
            f"verdict={event.verdict}",
            {
                "verdict": event.verdict,
                "confidence": event.confidence,
                "mode": event.mode,
                "rounds_used": event.rounds_used,
            },
        )

    def _on_correction_intent(self, event: Event) -> None:
        if not isinstance(event, CorrectionIntentEvent):
            return
        chain = self._resolve_chain(event.provenance_id, event.symbol, event.market)
        if chain is None:
            return
        self._append_step(
            chain,
            "CorrectionIntentEvent",
            event.change_type,
            {
                "intent_id": event.intent_id,
                "parameter_patch": event.parameter_patch,
                "confidence": event.confidence,
                "rationale": event.rationale,
            },
        )

    def _on_trade(self, event: Event) -> None:
        if not isinstance(event, TradeExecutedEvent):
            return
        prov = (event.provenance_id or "").strip()
        if not prov:
            logger.warning("TradeExecutedEvent missing provenance_id sym=%s", event.symbol)
            return
        chain = self.get_chain(prov)
        if chain is None:
            chain = SequenceChain(
                provenance_id=prov,
                symbol=event.symbol,
                market="CN",
                root_event_type="TradeExecutedEvent",
            )
            self._register_chain(chain)
        chain.status = "trade_linked"
        self._append_step(
            chain,
            "TradeExecutedEvent",
            f"{event.action} {event.quantity}@{event.price}",
            {
                "user_id": event.user_id,
                "action": event.action,
                "quantity": event.quantity,
                "price": event.price,
                "amount": event.amount,
            },
        )

    def _ensure_active_chain(self, symbol: str, market: str, root: str) -> SequenceChain:
        key = self._symbol_key(symbol, market)
        existing = self._active.get(key)
        if existing and existing.status == "active":
            return existing
        chain = SequenceChain(
            provenance_id=new_provenance_id(),
            symbol=symbol.strip().lower(),
            market=market.upper(),
            root_event_type=root,
            visibility=str(self._scope.get("visibility") or "private"),
            team_id=self._scope.get("team_id"),
            owner_user_id=self._scope.get("owner_user_id"),
        )
        self._register_chain(chain)
        self._active[key] = chain
        return chain

    def _resolve_chain(
        self, provenance_id: str, symbol: str, market: str
    ) -> SequenceChain | None:
        if provenance_id:
            chain = self.get_chain(provenance_id)
            if chain:
                return chain
        key = self._symbol_key(symbol, market)
        return self._active.get(key)

    def _register_chain(self, chain: SequenceChain) -> None:
        self._by_id[chain.provenance_id] = chain
        key = self._symbol_key(chain.symbol, chain.market)
        if chain.status == "active":
            self._active[key] = chain

    def _append_step(
        self,
        chain: SequenceChain,
        event_type: str,
        label: str,
        payload: dict[str, Any],
    ) -> None:
        step = SequenceStep(
            step_id=f"step-{uuid4().hex[:10]}",
            event_type=event_type,
            label=label,
            payload=payload,
            parent_step_id=chain.last_step_id(),
        )
        chain.steps.append(step)
        chain.updated_at = datetime.now().isoformat()
        self._store.append(chain)

    @staticmethod
    def _symbol_key(symbol: str, market: str) -> str:
        return f"{market.upper()}:{symbol.strip().lower()}"


def start_sequence_chain_service() -> SequenceChainService:
    """Bootstrap helper — wire EventBus provenance listener."""
    svc = SequenceChainService()
    svc.start()
    return svc
