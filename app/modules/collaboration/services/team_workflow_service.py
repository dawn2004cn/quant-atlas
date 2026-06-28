from __future__ import annotations

"""Team Workflow 2.0 — human + agent hybrid pipeline designer and runner (8.0 P1)."""

import uuid
from datetime import datetime, timezone
from typing import Any

from app.core.logger import get_logger
from app.domain.team_workflow_presets import (
    WORKFLOW_PRESET_REGISTRY,
    list_workflow_preset_summaries,
)
from app.domain.team_workflow_schema import TeamWorkflowDescriptor, TeamWorkflowNode, WorkflowNodeKind
from app.infrastructure.collaboration.team_workflow_store import TeamWorkflowStore

logger = get_logger(__name__)

_LEAD_ROLES = frozenset({"owner", "lead"})
_PAUSE_KINDS = frozenset({WorkflowNodeKind.HUMAN_TASK, WorkflowNodeKind.APPROVAL_GATE})


class TeamWorkflowService:
    """CRUD team pipelines and execute mixed human/agent steps."""

    def __init__(
        self,
        *,
        collaboration_repository: Any = None,
        store: TeamWorkflowStore | None = None,
        team_blackboard_service: Any | None = None,
        team_research_channel_service: Any | None = None,
        swarm_arbiter_service: Any | None = None,
        swarm_topology_service: Any | None = None,
    ) -> None:
        self._repo = collaboration_repository
        self._store = store or TeamWorkflowStore()
        self._blackboard = team_blackboard_service
        self._research = team_research_channel_service
        self._arbiter = swarm_arbiter_service
        self._topology = swarm_topology_service

    def list_presets(self) -> dict[str, Any]:
        return {"ok": True, "presets": list_workflow_preset_summaries()}

    def get_preset(self, preset_id: str) -> dict[str, Any]:
        wf = WORKFLOW_PRESET_REGISTRY.get(preset_id)
        if wf is None:
            return {"ok": False, "error": "preset_not_found"}
        return {"ok": True, "workflow": wf.model_dump()}

    def list_team_workflows(self, team_id: int) -> dict[str, Any]:
        return {"ok": True, "team_id": team_id, "items": self._store.list_workflows(team_id)}

    def get_team_workflow(self, team_id: int, workflow_id: str) -> dict[str, Any]:
        wf = self._resolve_workflow(team_id, workflow_id)
        if wf is None:
            return {"ok": False, "error": "workflow_not_found"}
        return {"ok": True, "workflow": wf.model_dump()}

    def save_team_workflow(
        self,
        user_id: int,
        team_id: int,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        if not self._is_team_lead(user_id, team_id):
            return {"ok": False, "error": "lead_required"}
        raw_id = (payload.get("id") or "").strip() or f"wf-{uuid.uuid4().hex[:8]}"
        payload["id"] = raw_id
        if not payload.get("name"):
            payload["name"] = raw_id
        try:
            wf = TeamWorkflowDescriptor.model_validate(payload)
        except Exception as exc:
            return {"ok": False, "error": "invalid_workflow", "details": str(exc)}
        saved = self._store.save_workflow(team_id, wf)
        validation = self.validate_workflow(saved)
        return {"ok": True, "workflow": saved.model_dump(), "validation": validation}

    def validate_workflow(self, workflow: TeamWorkflowDescriptor) -> dict[str, Any]:
        issues: list[str] = []
        kinds = {n.kind for n in workflow.nodes}
        if WorkflowNodeKind.START not in kinds:
            issues.append("missing_start_node")
        if WorkflowNodeKind.END not in kinds:
            issues.append("missing_end_node")
        if not workflow.entry_node:
            issues.append("missing_entry_node")
        agent_nodes = [n for n in workflow.nodes if n.kind == WorkflowNodeKind.AGENT_SWARM]
        for node in agent_nodes:
            if node.agent_topology_id and self._topology is not None:
                preset = self._topology.get_preset(node.agent_topology_id)
                if not preset.get("ok"):
                    issues.append(f"unknown_topology:{node.agent_topology_id}")
        return {"ok": not issues, "issues": issues, "node_count": len(workflow.nodes)}

    def start_run(
        self,
        user_id: int,
        team_id: int,
        workflow_id: str,
        *,
        context: dict[str, Any] | None = None,
        author_name: str = "Member",
    ) -> dict[str, Any]:
        if not self._is_team_member(user_id, team_id):
            return {"ok": False, "error": "team_access_denied"}

        wf = self._resolve_workflow(team_id, workflow_id)
        if wf is None:
            return {"ok": False, "error": "workflow_not_found"}

        run_id = f"wr-{uuid.uuid4().hex[:12]}"
        run: dict[str, Any] = {
            "run_id": run_id,
            "team_id": team_id,
            "workflow_id": workflow_id,
            "workflow_name": wf.name,
            "status": "running",
            "current_node_id": wf.entry_node or (wf.nodes[0].id if wf.nodes else ""),
            "pause_reason": None,
            "context": dict(context or {}),
            "steps": [],
            "started_by": user_id,
            "author_name": author_name,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        self._store.append_run(team_id, run)
        return self._execute_until_paused(team_id, run)

    def advance_run(
        self,
        user_id: int,
        team_id: int,
        run_id: str,
        *,
        action: str = "complete",
        note: str = "",
    ) -> dict[str, Any]:
        run = self._store.get_run(team_id, run_id)
        if run is None:
            return {"ok": False, "error": "run_not_found"}
        if run.get("status") not in {"paused", "running"}:
            return {"ok": False, "error": "run_not_active", "status": run.get("status")}

        wf = self._resolve_workflow(team_id, str(run.get("workflow_id") or ""))
        if wf is None:
            return {"ok": False, "error": "workflow_not_found"}

        node_id = str(run.get("current_node_id") or "")
        node = wf.node_map().get(node_id)
        if node is None:
            return {"ok": False, "error": "invalid_current_node"}

        if node.kind == WorkflowNodeKind.APPROVAL_GATE:
            if not self._is_team_lead(user_id, team_id):
                return {"ok": False, "error": "lead_approval_required"}
            if action == "reject":
                run["status"] = "rejected"
                run["pause_reason"] = "lead_rejected"
                run["updated_at"] = datetime.now(timezone.utc).isoformat()
                self._store.update_run(team_id, run_id, run)
                return {"ok": True, "run": run}
        elif node.kind == WorkflowNodeKind.HUMAN_TASK:
            if not self._is_team_member(user_id, team_id):
                return {"ok": False, "error": "team_access_denied"}

        step_out = {
            "node_id": node_id,
            "kind": node.kind.value,
            "status": "ok",
            "action": action,
            "note": (note or "")[:500],
            "completed_by": user_id,
        }
        steps = list(run.get("steps") or [])
        steps.append(step_out)
        run["steps"] = steps
        run["status"] = "running"
        run["pause_reason"] = None

        next_id = wf.next_node_id(node_id)
        if not next_id:
            run["status"] = "completed"
            run["current_node_id"] = node_id
        else:
            run["current_node_id"] = next_id
        run["updated_at"] = datetime.now(timezone.utc).isoformat()
        self._store.update_run(team_id, run_id, run)
        if run["status"] == "completed":
            return {"ok": True, "run": run}
        return self._execute_until_paused(team_id, run)

    def list_runs(self, team_id: int, *, limit: int = 30) -> dict[str, Any]:
        rows = self._store.list_runs(team_id, limit=limit)
        return {"ok": True, "team_id": team_id, "runs": rows, "count": len(rows)}

    def designer_blocks(self) -> dict[str, Any]:
        return {
            "ok": True,
            "blocks": [
                {"kind": "human_task", "label": "人工任务"},
                {"kind": "approval_gate", "label": "Lead 审批"},
                {"kind": "blackboard_post", "label": "黑板证据"},
                {"kind": "research_publish", "label": "投研流发布"},
                {"kind": "agent_swarm", "label": "Agent Swarm"},
                {"kind": "arbiter", "label": "团队仲裁"},
            ],
        }

    def _execute_until_paused(self, team_id: int, run: dict[str, Any]) -> dict[str, Any]:
        wf = self._resolve_workflow(team_id, str(run.get("workflow_id") or ""))
        if wf is None:
            return {"ok": False, "error": "workflow_not_found"}

        run_id = str(run.get("run_id") or "")
        safety = 0
        while run.get("status") == "running" and safety < 24:
            safety += 1
            node_id = str(run.get("current_node_id") or "")
            node = wf.node_map().get(node_id)
            if node is None:
                run["status"] = "failed"
                run["error"] = "unknown_node"
                break
            if node.kind == WorkflowNodeKind.END:
                run["status"] = "completed"
                break
            if node.kind in _PAUSE_KINDS:
                run["status"] = "paused"
                run["pause_reason"] = node.kind.value
                break

            result = self._execute_node(team_id, run, node)
            steps = list(run.get("steps") or [])
            steps.append(
                {
                    "node_id": node_id,
                    "kind": node.kind.value,
                    "status": "ok" if result.get("ok") else "error",
                    "output": result,
                }
            )
            run["steps"] = steps
            if not result.get("ok"):
                run["status"] = "failed"
                run["error"] = result.get("error")
                break

            next_id = wf.next_node_id(node_id)
            if not next_id:
                run["status"] = "completed"
            else:
                run["current_node_id"] = next_id
            run["updated_at"] = datetime.now(timezone.utc).isoformat()
            self._store.update_run(team_id, run_id, run)
            if run["status"] == "completed":
                break

        self._store.update_run(team_id, run_id, run)
        return {"ok": True, "run": run}

    def _execute_node(
        self,
        team_id: int,
        run: dict[str, Any],
        node: TeamWorkflowNode,
    ) -> dict[str, Any]:
        ctx = run.get("context") or {}
        symbol = str(ctx.get("symbol") or "").strip() or None
        market = str(ctx.get("market") or "CN").upper()
        user_id = int(run.get("started_by") or 0)
        author = str(run.get("author_name") or "Member")

        if node.kind == WorkflowNodeKind.START:
            return {"ok": True, "message": "pipeline_started"}

        if node.kind == WorkflowNodeKind.BLACKBOARD_POST:
            if self._blackboard is None:
                return {"ok": False, "error": "blackboard_unavailable"}
            text = str(ctx.get("evidence_text") or ctx.get("topic") or "工作流自动证据")
            return self._blackboard.submit_note(
                team_id=team_id,
                user_id=user_id,
                evidence_key=str(node.config.get("evidence_key") or "workflow"),
                evidence_value=text[:500],
                agent_role=str(node.agent_role or "workflow_runner"),
                symbol=symbol,
                narrative=text[:300],
            )

        if node.kind == WorkflowNodeKind.RESEARCH_PUBLISH:
            if self._research is None:
                return {"ok": False, "error": "research_channel_unavailable"}
            summary = str(ctx.get("publish_summary") or ctx.get("topic") or "团队流水线结论发布")
            return self._research.publish_research(
                team_id=team_id,
                user_id=user_id,
                author_name=author,
                content_text=summary,
                symbol=symbol,
                provenance_id=str(ctx.get("provenance_id") or "") or None,
            )

        if node.kind == WorkflowNodeKind.ARBITER:
            if self._blackboard is None:
                return {"ok": False, "error": "blackboard_unavailable"}
            return self._blackboard.synthesize_consensus(team_id, symbol=symbol)

        if node.kind == WorkflowNodeKind.AGENT_SWARM:
            if not symbol:
                return {"ok": False, "error": "symbol_required_in_context"}
            topo_id = node.agent_topology_id or "integrated_parallel"
            topo_note = ""
            if self._topology is not None:
                preset = self._topology.get_preset(topo_id)
                if preset.get("ok"):
                    topo_note = str(preset.get("topology", {}).get("name") or topo_id)
            arbiter_out = None
            if self._arbiter is not None:
                try:
                    arbiter_out = self._arbiter.consensus_only(symbol.upper(), market, use_llm=False)
                except Exception as exc:
                    logger.warning("workflow agent_swarm arbiter: %s", exc)
            self._inject_swarm_round(symbol, market, topo_id, topo_note)
            return {
                "ok": True,
                "topology_id": topo_id,
                "topology_name": topo_note,
                "arbiter": arbiter_out,
            }

        return {"ok": True, "message": f"skipped_kind_{node.kind.value}"}

    def _inject_swarm_round(
        self,
        symbol: str,
        market: str,
        topology_id: str,
        topology_name: str,
    ) -> None:
        try:
            from app.agents.research.debate_bus import publish_debate_round

            publish_debate_round(
                ticker=symbol,
                agent_role="macro_analyst",
                chunk=(
                    f"[Team Workflow] Swarm 拓扑 {topology_name or topology_id} "
                    f"已对 {symbol} 执行分析节点。"
                ),
                round_num=800,
                debate_phase="team_workflow",
                market=market,
            )
        except Exception as exc:
            logger.debug("workflow debate inject: %s", exc)

    def _resolve_workflow(self, team_id: int, workflow_id: str) -> TeamWorkflowDescriptor | None:
        saved = self._store.get_workflow(team_id, workflow_id)
        if saved is not None:
            return saved
        preset = WORKFLOW_PRESET_REGISTRY.get(workflow_id)
        if preset is not None:
            return preset.model_copy(update={"team_id": team_id})
        return None

    def _is_team_member(self, user_id: int, team_id: int) -> bool:
        teams = self._repo.list_user_teams(user_id)
        return any(int(t.get("team_id") or 0) == team_id for t in teams)

    def _is_team_lead(self, user_id: int, team_id: int) -> bool:
        teams = self._repo.list_user_teams(user_id)
        for row in teams:
            if int(row.get("team_id") or 0) != team_id:
                continue
            if str(row.get("role") or "").lower() in _LEAD_ROLES:
                return True
        return False


__all__ = ["TeamWorkflowService"]
