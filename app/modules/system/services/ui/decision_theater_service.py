from __future__ import annotations

"""Decision Theater — immersive research pipeline 3D scene (Quant Atlas 9.0 Step Five)."""

import math
from typing import Any

from app.core.event_bus import get_event_bus
from app.core.logger import get_logger
from app.domain.decision_replay_scene import DecisionReplayScene, SceneEdge, SceneNode
from app.domain.verification import list_pending

logger = get_logger(__name__)

_PIPELINE_STAGES = [
    ("ingest", "数据入库", "#0ea5e9"),
    ("dump_bin", "Qlib 转换", "#6366f1"),
    ("rd_agent", "因子演化", "#a855f7"),
    ("qlib_gate", "回测门禁", "#f59e0b"),
    ("agent_debate", "Agent 辩论", "#22c55e"),
    ("decision", "决策输出", "#64748b"),
]


class DecisionTheaterService:
    """Compile research pipeline + EventBus pulse into a navigable 3D theater."""

    def __init__(
        self,
        *,
        qlib_pipeline_service: Any | None = None,
        rdagent_run_service: Any | None = None,
        enable_qlib: bool = False,
        enable_rd_agent: bool = False,
    ) -> None:
        self._qlib = qlib_pipeline_service
        self._rd = rdagent_run_service
        self._enable_qlib = enable_qlib
        self._enable_rd = enable_rd_agent

    def build_theater(self, user_id: int | str | None = None) -> dict[str, Any]:
        pipeline = self._load_pipeline_snapshot()
        steps = {s.get("id"): s for s in (pipeline.get("steps") or []) if isinstance(s, dict)}
        recent = get_event_bus().list_recent_events(limit=30)
        pending = list_pending()

        nodes: list[SceneNode] = []
        edges: list[SceneEdge] = []
        span = len(_PIPELINE_STAGES)
        for idx, (sid, label, color) in enumerate(_PIPELINE_STAGES):
            step = steps.get(sid.replace("agent_debate", "rd_agent"), {})
            if sid == "agent_debate":
                step = {"ok": True, "detail": "DebateRoundEvent 驱动"}
            elif sid == "decision":
                step = {"ok": len(recent) > 0, "detail": f"{len(recent)} 条近期事件"}
            ok = bool(step.get("ok", sid not in ("dump_bin", "rd_agent", "qlib_gate") or self._enable_qlib))
            nodes.append(
                SceneNode(
                    id=f"stage_{sid}",
                    type="pipeline_stage",
                    label=label,
                    color=color if ok else "#ef4444",
                    size=0.55 if ok else 0.45,
                    x=float(idx * 3.2 - span * 1.6),
                    y=0.0,
                    z=0.0,
                    meta={"stage_id": sid, "ok": ok, "detail": step.get("detail", "")},
                )
            )
            if idx > 0:
                prev_id = f"stage_{_PIPELINE_STAGES[idx - 1][0]}"
                edges.append(
                    SceneEdge(
                        from_id=prev_id,
                        to_id=f"stage_{sid}",
                        relation="pipeline_flow",
                        color="#94a3b8" if ok else "#fca5a5",
                    )
                )

        # Event satellites
        for i, evt in enumerate(recent[:12]):
            angle = (i / max(1, min(12, len(recent)))) * math.pi * 2
            r = 8.0
            nodes.append(
                SceneNode(
                    id=f"evt_{i}",
                    type="event",
                    label=str(evt.get("event") or "Event")[:24],
                    color="#38bdf8",
                    size=0.28,
                    x=math.cos(angle) * r,
                    y=1.2 + (i % 3) * 0.4,
                    z=math.sin(angle) * r,
                    meta={"event": evt},
                )
            )
            edges.append(
                SceneEdge(
                    from_id="stage_agent_debate",
                    to_id=f"evt_{i}",
                    relation="emitted",
                    color="#38bdf840",
                )
            )

        # Data truth pending orbs
        for j, (key, reason) in enumerate(list(pending.items())[:6]):
            nodes.append(
                SceneNode(
                    id=f"truth_{j}",
                    type="data_truth_alert",
                    label=key.split(":")[-1][:12],
                    color="#ef4444",
                    size=0.35,
                    x=-10.0,
                    y=2.5,
                    z=float(j * 1.8 - 3),
                    meta={"reason": reason[:120]},
                )
            )
            edges.append(
                SceneEdge(
                    from_id="stage_ingest",
                    to_id=f"truth_{j}",
                    relation="verification_pending",
                    color="#ef4444",
                )
            )

        scene = DecisionReplayScene(
            schema_version="v2_theater",
            subject=f"research_pipeline:user={user_id or 'anon'}",
            nodes=nodes,
            edges=edges,
            camera={"x": 0, "y": 12, "z": 24},
            bounds={"min_x": -14, "max_x": 14, "min_z": -12, "max_z": 12},
        )
        return {
            "ok": True,
            "scene": scene.to_dict(),
            "pipeline_summary": {
                "steps_ok": sum(1 for s in (pipeline.get("steps") or []) if s.get("ok")),
                "step_count": len(pipeline.get("steps") or []),
                "recent_events": len(recent),
                "pending_truth": len(pending),
            },
            "evidence": "研究流水线阶段 + EventBus 脉冲 + 数据真值待核验节点",
            "confidence": 0.88,
        }

    def _load_pipeline_snapshot(self) -> dict[str, Any]:
        try:
            from app.modules.data.services.research_pipeline_snapshot import (
                build_research_pipeline_snapshot,
            )

            return build_research_pipeline_snapshot(
                enable_qlib=self._enable_qlib,
                enable_rd_agent=self._enable_rd,
                qlib_pipeline_service=self._qlib,
                rdagent_run_service=self._rd,
            )
        except Exception as exc:
            logger.warning("decision_theater pipeline snapshot: %s", exc)
            return {"steps": []}


__all__ = ["DecisionTheaterService"]
