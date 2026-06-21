from __future__ import annotations
"""Built-in team workflow presets for Pipeline Designer."""

from app.domain.team_workflow_schema import (
    TeamWorkflowDescriptor,
    TeamWorkflowEdge,
    TeamWorkflowNode,
    WorkflowNodeKind,
)


def preset_lead_review_pipeline() -> TeamWorkflowDescriptor:
    """Analyst evidence → agent swarm → lead approval → arbiter → publish."""
    nodes = [
        TeamWorkflowNode(id="start", kind=WorkflowNodeKind.START, label="开始"),
        TeamWorkflowNode(
            id="human_evidence",
            kind=WorkflowNodeKind.HUMAN_TASK,
            label="分析师提交证据",
            assignee_role="member",
            config={"task_type": "submit_evidence"},
        ),
        TeamWorkflowNode(
            id="agent_swarm",
            kind=WorkflowNodeKind.AGENT_SWARM,
            label="Agent Swarm 分析",
            agent_topology_id="integrated_parallel",
            agent_role="macro",
        ),
        TeamWorkflowNode(
            id="blackboard",
            kind=WorkflowNodeKind.BLACKBOARD_POST,
            label="写入团队黑板",
        ),
        TeamWorkflowNode(
            id="lead_approve",
            kind=WorkflowNodeKind.APPROVAL_GATE,
            label="Lead 审批",
            assignee_role="owner",
        ),
        TeamWorkflowNode(id="arbiter", kind=WorkflowNodeKind.ARBITER, label="团队仲裁共识"),
        TeamWorkflowNode(
            id="publish",
            kind=WorkflowNodeKind.RESEARCH_PUBLISH,
            label="发布投研流",
        ),
        TeamWorkflowNode(id="end", kind=WorkflowNodeKind.END, label="结束"),
    ]
    edges = [
        TeamWorkflowEdge(**{"from": "start", "to": "human_evidence"}),
        TeamWorkflowEdge(**{"from": "human_evidence", "to": "agent_swarm"}),
        TeamWorkflowEdge(**{"from": "agent_swarm", "to": "blackboard"}),
        TeamWorkflowEdge(**{"from": "blackboard", "to": "lead_approve"}),
        TeamWorkflowEdge(**{"from": "lead_approve", "to": "arbiter"}),
        TeamWorkflowEdge(**{"from": "arbiter", "to": "publish"}),
        TeamWorkflowEdge(**{"from": "publish", "to": "end"}),
    ]
    return TeamWorkflowDescriptor(
        id="lead_review_pipeline",
        name="Lead 审批投研流水线",
        description="成员证据 → Swarm 分析 → 黑板 → Lead 审批 → 仲裁 → 投研流发布",
        nodes=nodes,
        edges=edges,
        entry_node="start",
        exit_node="end",
    )


def preset_fast_agent_loop() -> TeamWorkflowDescriptor:
    nodes = [
        TeamWorkflowNode(id="start", kind=WorkflowNodeKind.START, label="开始"),
        TeamWorkflowNode(
            id="swarm",
            kind=WorkflowNodeKind.AGENT_SWARM,
            label="辩论仲裁流水线",
            agent_topology_id="debate_pipeline",
        ),
        TeamWorkflowNode(id="arbiter", kind=WorkflowNodeKind.ARBITER, label="黑板共识"),
        TeamWorkflowNode(
            id="publish",
            kind=WorkflowNodeKind.RESEARCH_PUBLISH,
            label="发布结论",
        ),
        TeamWorkflowNode(id="end", kind=WorkflowNodeKind.END, label="结束"),
    ]
    edges = [
        TeamWorkflowEdge(**{"from": "start", "to": "swarm"}),
        TeamWorkflowEdge(**{"from": "swarm", "to": "arbiter"}),
        TeamWorkflowEdge(**{"from": "arbiter", "to": "publish"}),
        TeamWorkflowEdge(**{"from": "publish", "to": "end"}),
    ]
    return TeamWorkflowDescriptor(
        id="fast_agent_loop",
        name="快速 Agent 闭环",
        description="全自动 Agent 分析 → 仲裁 → 投研流（无人工卡点）",
        nodes=nodes,
        edges=edges,
        entry_node="start",
        exit_node="end",
    )


WORKFLOW_PRESET_REGISTRY: dict[str, TeamWorkflowDescriptor] = {
    "lead_review_pipeline": preset_lead_review_pipeline(),
    "fast_agent_loop": preset_fast_agent_loop(),
}


def list_workflow_preset_summaries() -> list[dict[str, str]]:
    return [
        {
            "id": wf.id,
            "name": wf.name,
            "description": wf.description,
        }
        for wf in WORKFLOW_PRESET_REGISTRY.values()
    ]
