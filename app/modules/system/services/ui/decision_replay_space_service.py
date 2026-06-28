from __future__ import annotations

"""Decision Replay Space — 2.5D/3D scene from behavior topology + evidence timeline (8.0 P2)."""

import math
from typing import Any

from app.core.logger import get_logger
from app.domain.decision_replay_scene import DecisionReplayScene, SceneEdge, SceneNode

logger = get_logger(__name__)

_NODE_COLORS = {
    "user": "#4f46e5",
    "sector": "#0ea5e9",
    "symbol": "#22c55e",
    "event": "#f59e0b",
    "debate": "#a855f7",
    "decision": "#64748b",
    "decision_win": "#16a34a",
    "decision_loss": "#dc2626",
    "bias": "#ef4444",
    "replay": "#38bdf8",
}


class DecisionReplaySpaceService:
    """Compile immersive decision replay scenes for WebGL rendering."""

    def __init__(
        self,
        *,
        user_knowledge_service: Any | None = None,
        ai_evidence_service: Any | None = None,
    ) -> None:
        self._knowledge = user_knowledge_service
        self._ai_evidence = ai_evidence_service

    def build_space(
        self,
        user_id: str | int,
        *,
        symbol: str | None = None,
        market: str = "CN",
        minutes_back: int = 120,
    ) -> dict[str, Any]:
        if self._knowledge is None:
            return {"ok": False, "error": "user_knowledge_unavailable"}

        profile = self._knowledge.get_profile(user_id)
        topology = self._knowledge.analyze_topology(user_id)
        sym = (symbol or "").strip().upper() or None
        mkt = (market or "CN").strip().upper()

        timeline: dict[str, Any] = {"nodes": []}
        if sym:
            timeline = self._build_timeline(sym, mkt, minutes_back=minutes_back)

        scene = self._compile_scene(
            user_id=str(user_id),
            profile=profile,
            topology=topology,
            timeline=timeline,
            symbol=sym,
            market=mkt,
        )
        return {
            "ok": True,
            "scene": scene.to_dict(),
            "behavior_topology": topology,
            "timeline_summary": {
                "symbol": sym,
                "market": mkt,
                "node_count": len(timeline.get("nodes") or []),
                "minutes_back": minutes_back,
            },
        }

    def _build_timeline(self, symbol: str, market: str, *, minutes_back: int) -> dict[str, Any]:
        try:
            from app.modules.ai_agent.services.evidence_replay_service import EvidenceReplayService

            svc = EvidenceReplayService(ai_evidence_service=self._ai_evidence)
            return svc.build_timeline(symbol, market=market, minutes_back=minutes_back)
        except Exception as exc:
            logger.warning("decision_replay_space timeline: %s", exc)
            return {"nodes": []}

    def _compile_scene(
        self,
        *,
        user_id: str,
        profile: dict[str, Any],
        topology: dict[str, Any],
        timeline: dict[str, Any],
        symbol: str | None,
        market: str,
    ) -> DecisionReplayScene:
        nodes: list[SceneNode] = []
        edges: list[SceneEdge] = []
        user_nid = f"user:{user_id}"
        nodes.append(
            SceneNode(
                id=user_nid,
                type="user",
                label="我",
                color=_NODE_COLORS["user"],
                size=0.9,
                x=0,
                y=0,
                z=0,
            )
        )

        topo = topology.get("topology") or {}
        topo_nodes = list(topo.get("nodes") or [])
        topo_edges = list(topo.get("edges") or [])

        sectors = [n for n in topo_nodes if n.get("type") == "sector"]
        symbols = [n for n in topo_nodes if n.get("type") == "symbol"]
        self._place_ring(nodes, sectors, radius=4.5, y=2.0, color_key="sector", size=0.55)
        self._place_ring(nodes, symbols, radius=7.0, y=1.0, color_key="symbol", size=0.5)

        for edge in topo_edges:
            edges.append(
                SceneEdge(
                    from_id=str(edge.get("from") or ""),
                    to_id=str(edge.get("to") or ""),
                    relation=str(edge.get("relation") or "researched"),
                )
            )

        patterns = list(profile.get("decision_patterns") or [])[-12:]
        for idx, pat in enumerate(patterns):
            outcome = str(pat.get("outcome") or "").lower()
            is_win = outcome in ("win", "profit", "success", "bullish", "correct")
            angle = (idx / max(len(patterns), 1)) * math.pi * 2
            nid = f"decision:{idx}"
            nodes.append(
                SceneNode(
                    id=nid,
                    type="decision_win" if is_win else "decision_loss",
                    label=outcome or "decision",
                    color=_NODE_COLORS["decision_win"] if is_win else _NODE_COLORS["decision_loss"],
                    size=0.35,
                    x=round(3.2 * math.cos(angle), 2),
                    y=-1.2,
                    z=round(3.2 * math.sin(angle), 2),
                    meta={"symbols": pat.get("symbols") or [], "sectors": pat.get("sectors") or []},
                )
            )
            edges.append(SceneEdge(from_id=user_nid, to_id=nid, relation="decision_pattern"))

        for idx, bias in enumerate(topology.get("cognitive_biases") or []):
            nid = f"bias:{idx}"
            nodes.append(
                SceneNode(
                    id=nid,
                    type="bias",
                    label=str(bias.get("type") or "bias"),
                    color=_NODE_COLORS["bias"],
                    size=0.42,
                    x=-5.5,
                    y=1.5 + idx * 0.8,
                    z=2.0,
                    meta=bias,
                )
            )
            edges.append(SceneEdge(from_id=user_nid, to_id=nid, relation="cognitive_bias"))

        timeline_nodes = list(timeline.get("nodes") or [])
        for idx, item in enumerate(timeline_nodes[-24:]):
            nid = f"replay:{idx}"
            kind = str(item.get("kind") or item.get("event") or "replay")
            node_type = "debate" if "debate" in kind.lower() else "replay"
            nodes.append(
                SceneNode(
                    id=nid,
                    type=node_type,
                    label=kind[:24],
                    color=_NODE_COLORS.get(node_type, _NODE_COLORS["replay"]),
                    size=0.38,
                    x=round((idx % 6) * 1.4 - 3.5, 2),
                    y=0.4 + (idx // 6) * 0.3,
                    z=round(10.0 + idx * 1.6, 2),
                    meta={
                        "timestamp": item.get("timestamp"),
                        "summary": (item.get("summary") or item.get("evidence_summary") or "")[:200],
                    },
                )
            )
            anchor = user_nid
            if symbol:
                sym_nid = f"symbol:{symbol.lower()}"
                if any(n.id == sym_nid for n in nodes):
                    anchor = sym_nid
            edges.append(SceneEdge(from_id=anchor, to_id=nid, relation="timeline", color="#38bdf8"))

        bounds = self._compute_bounds(nodes)
        subject = f"{symbol} @ {market}" if symbol else f"user:{user_id}"
        return DecisionReplayScene(
            subject=subject,
            symbol=symbol,
            market=market,
            nodes=nodes,
            edges=edges,
            camera={"x": 0, "y": 10, "z": 22},
            bounds=bounds,
        )

    @staticmethod
    def _place_ring(
        nodes: list[SceneNode],
        items: list[dict[str, Any]],
        *,
        radius: float,
        y: float,
        color_key: str,
        size: float,
    ) -> None:
        count = len(items)
        if count == 0:
            return
        for idx, item in enumerate(items):
            angle = (idx / count) * math.pi * 2
            nid = str(item.get("id") or f"node:{idx}")
            if any(n.id == nid for n in nodes):
                continue
            nodes.append(
                SceneNode(
                    id=nid,
                    type=color_key,
                    label=str(item.get("label") or nid),
                    color=_NODE_COLORS.get(color_key, "#6366f1"),
                    size=size,
                    x=round(radius * math.cos(angle), 2),
                    y=y,
                    z=round(radius * math.sin(angle), 2),
                )
            )

    @staticmethod
    def _compute_bounds(nodes: list[SceneNode]) -> dict[str, float]:
        if not nodes:
            return {"min_x": 0, "max_x": 0, "min_y": 0, "max_y": 0, "min_z": 0, "max_z": 0}
        xs = [n.x for n in nodes]
        ys = [n.y for n in nodes]
        zs = [n.z for n in nodes]
        return {
            "min_x": min(xs),
            "max_x": max(xs),
            "min_y": min(ys),
            "max_y": max(ys),
            "min_z": min(zs),
            "max_z": max(zs),
        }


__all__ = ["DecisionReplaySpaceService"]
