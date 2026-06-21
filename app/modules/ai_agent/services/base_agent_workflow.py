from __future__ import annotations
from app.domain.dto.service_result import GenericResponseDTO
"""Base Agent Workflow Engine for unified agent orchestration."""


import concurrent.futures
import uuid
from datetime import datetime
from typing import Any

from app.core.logger import get_logger
from app.domain.dto.agent_workflow_dto import (
    AgentConfig,
    AgentContext,
    AgentResult,
    AgentSignal,
    WorkflowConfig,
    WorkflowState,
)

logger = get_logger(__name__)


class BaseAgentWorkflowEngine:
    """Base class for agent workflow orchestration.

    Provides unified management of multi-agent conversation contexts and state.
    Can be extended with LangGraph or similar tools for complex workflows.
    """

    def __init__(
        self,
        ai_adapter: object,
        config: WorkflowConfig | None = None,
    ):
        self._ai_adapter = ai_adapter
        self._config = config or WorkflowConfig(workflow_id=str(uuid.uuid4()))
        self._workflow_states: dict[str, WorkflowState] = {}

    def create_workflow(
        self,
        symbol: str,
        market: str,
    ) -> WorkflowState:
        """Create a new workflow state."""
        workflow_id = self._config.workflow_id or str(uuid.uuid4())

        state = WorkflowState(
            workflow_id=workflow_id,
            symbol=symbol,
            market=market,
            status="created",
        )
        self._workflow_states[workflow_id] = state
        return state

    def run_workflow(
        self,
        context: AgentContext,
        agent_configs: list[AgentConfig] | None = None,
        max_parallel: int | None = None,
    ) -> WorkflowState:
        """Run a complete workflow with multiple agents."""
        agents = agent_configs or self._config.agents
        workflow_id = self._config.workflow_id or str(uuid.uuid4())
        max_workers = max_parallel or self._config.max_parallel

        state = self._workflow_states.get(workflow_id) or self.create_workflow(
            context.symbol, context.market
        )
        state.status = "running"

        try:
            results = self._run_agents_parallel(
                agents=[a for a in agents if a.enabled],
                context=context,
                max_workers=max_workers,
            )
            state.agent_results = results
            state.status = "completed"
        except Exception as e:
            logger.exception("Workflow error")
            state.status = "failed"
            state.error = str(e)

        state.end_time = datetime.now().isoformat()
        self._workflow_states[workflow_id] = state
        return state

    def _run_agents_parallel(
        self,
        agents: list[AgentConfig],
        context: AgentContext,
        max_workers: int = 6,
    ) -> list[AgentResult]:
        """Run agents in parallel using thread pool."""
        results: list[AgentResult] = []

        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(self._run_single_agent, agent, context): agent
                for agent in agents
            }
            for future in concurrent.futures.as_completed(futures):
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    agent = futures[future]
                    logger.exception(f"Agent {agent.id} failed")
                    results.append(
                        AgentResult(
                            agent_id=agent.id,
                            agent_name=agent.name,
                            agent_role=agent.role,
                            signal=AgentSignal.NEUTRAL,
                            reasoning=f"Error: {e!s}",
                        )
                    )

        return results

    def _run_single_agent(self, agent: AgentConfig, context: AgentContext) -> AgentResult:
        """Run a single agent with the given context."""
        if self._ai_adapter is None:
            logger.warning(f"Agent {agent.id}: ai_adapter is None, using template response")
            return AgentResult(
                agent_id=agent.id,
                agent_name=agent.name,
                agent_role=agent.role,
                signal=AgentSignal.NEUTRAL,
                reasoning=f"[Template] {agent.role}: 分析功能需要配置 LLM 适配器。当前为模板响应。",
                metrics={"template": True},
            )
        try:
            res = self._ai_adapter.analyze(
                symbol=context.symbol,
                market=context.market,
                context=context.model_dump(),
                mode="committee",
                custom_prompt=agent.prompt_prefix,
            )

            narrative = res.get("analysis", "")
            signal = AgentSignal.NEUTRAL
            if "买入" in narrative or "看涨" in narrative or "持有" in narrative:
                signal = AgentSignal.BULLISH
            if "减持" in narrative or "卖出" in narrative or "风险" in narrative:
                signal = AgentSignal.BEARISH
            if "警告" in narrative or "超标" in narrative:
                signal = AgentSignal.RISK

            return AgentResult(
                agent_id=agent.id,
                agent_name=agent.name,
                agent_role=agent.role,
                signal=signal,
                reasoning=narrative,
                metrics=res.get("metrics", {}),
            )
        except Exception:
            logger.exception(f"Agent {agent.id} error")
            raise

    def compute_consensus(self, results: list[AgentResult], agents: list[AgentConfig]) -> GenericResponseDTO:
        """Compute consensus from agent results."""
        scores = {"bullish": 0.0, "bearish": 0.0, "neutral": 0.0, "risk": 0.0}
        agent_map = {a.id: a for a in agents}

        for r in results:
            agent = agent_map.get(r.agent_id)
            if agent:
                scores[r.signal.value] += agent.weight

        final_action = max(scores, key=scores.get)
        confidence = scores[final_action] * 100

        return {
            "final_action": final_action,
            "confidence": f"{confidence:.1f}%",
            "votes": {k: f"{v*100:.0f}%" for k, v in scores.items()},
        }

    def get_workflow_state(self, workflow_id: str) -> WorkflowState | None:
        """Get workflow state by ID."""
        return self._workflow_states.get(workflow_id)
