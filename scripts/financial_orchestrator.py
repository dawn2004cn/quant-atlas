"""
多 Agent 金融分析编排器 — 协调 4 个金融智能体 + Quant Atlas 量化基础设施。

功能：
- 根据任务自动路由到正确的 Agent
- 并行执行互不依赖的研究任务
- 聚合输出，确保数据一致性
- 集成 Quant Atlas 回测引擎和图表系统

用法：
    # 在 Claude Code 中，chinese-quant-coordinator 智能体会自动使用此模块
    # 作为跨 Agent 交接的参考实现

数据源优先级：
    1. Wind MCP (付费) — 最全面
    2. iFind MCP (付费) — 精确数据
    3. AkShare MCP (免费) — 基础数据
    4. China News MCP (免费) — 新闻
"""

from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Optional

# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------


class AgentName(str, Enum):
    MARKET_RESEARCHER = "china-market-researcher"
    MODEL_BUILDER = "china-model-builder"
    EARNINGS_REVIEWER = "china-earnings-reviewer"
    PITCH_AGENT = "china-pitch-agent"


class DataSource(str, Enum):
    WIND = "wind"
    IFIND = "ifind"
    AKSHARE = "akshare"
    CHINA_NEWS = "china-news"


@dataclass
class TaskRequest:
    """发送给子 Agent 的任务请求。"""
    agent: AgentName
    prompt: str
    stock_code: str
    priority: int = 1  # 1=high, 2=medium, 3=low

    # 依赖：此任务等待哪些其他任务完成
    depends_on: list[str] = field(default_factory=list)


@dataclass
class TaskResult:
    """子 Agent 的执行结果。"""
    task_id: str
    agent: AgentName
    stock_code: str
    output: str
    data_source_used: DataSource
    timestamp: float = field(default_factory=time.time)
    error: Optional[str] = None


@dataclass
class AnalysisPipeline:
    """一条完整的金融分析流水线。"""
    stock_code: str
    requests: list[TaskRequest] = field(default_factory=list)
    results: dict[str, TaskResult] = field(default_factory=dict)
    started_at: float = field(default_factory=time.time)

    def add_task(
        self,
        agent: AgentName,
        prompt: str,
        depends_on: list[str] | None = None,
        priority: int = 1,
    ) -> str:
        """添加一个子任务，返回 task_id。"""
        task_id = f"task_{len(self.requests)}"
        self.requests.append(
            TaskRequest(
                agent=agent,
                prompt=prompt,
                stock_code=self.stock_code,
                priority=priority,
                depends_on=depends_on or [],
            )
        )
        return task_id


# ---------------------------------------------------------------------------
# Router — 根据自然语言任务自动选择 Agent
# ---------------------------------------------------------------------------

ROUTER_RULES: list[tuple[list[str], AgentName]] = [
    # 关键词 → Agent 映射
    (["估值", "估值建模", "DCF", "LBO", "三表", "财务模型", "model"], AgentName.MODEL_BUILDER),
    (["财报", "业绩", "earnings", "季报", "年报", "净利润", "营收"], AgentName.EARNINGS_REVIEWER),
    (["行业", "竞争", "板块", "sector", "industry", "竞争格局", "赛道"], AgentName.MARKET_RESEARCHER),
    (["路演", "pitch", "deck", "comps", "可比", "对标", "football"], AgentName.PITCH_AGENT),
]


def route_task(prompt: str) -> AgentName:
    """根据 prompt 关键词路由到最合适的 Agent。"""
    prompt_lower = prompt.lower()
    for keywords, agent in ROUTER_RULES:
        for kw in keywords:
            if kw.lower() in prompt_lower:
                return agent
    # 默认：行业研究
    return AgentName.MARKET_RESEARCHER


# ---------------------------------------------------------------------------
# Orchestrator — 按依赖关系调度 Agent 执行
# ---------------------------------------------------------------------------


class FinancialOrchestrator:
    """
    多 Agent 金融分析编排器。

    用法：
        orch = FinancialOrchestrator()
        pipeline = orch.create_pipeline("600519")

        # 添加任务（可指定依赖关系）
        t1 = pipeline.add_task(
            AgentName.MARKET_RESEARCHER,
            "分析贵州茅台所处白酒行业的竞争格局",
        )
        t2 = pipeline.add_task(
            AgentName.MODEL_BUILDER,
            "为贵州茅台构建 DCF 模型",
            depends_on=[t1],  # 依赖行业分析结果
        )

        # 执行（通过 Agent 工具调度和执行）
        results = await orch.execute_pipeline(pipeline)
    """

    def __init__(self) -> None:
        self.data_source = DataSource.AKSHARE  # 默认免费源

    def create_pipeline(self, stock_code: str) -> AnalysisPipeline:
        """创建一个分析流水线。"""
        return AnalysisPipeline(stock_code=stock_code)

    def auto_build_pipeline(
        self,
        stock_code: str,
        request_type: str,
    ) -> AnalysisPipeline:
        """
        根据自然语言请求自动构建多 Agent 流水线。

        Args:
            stock_code: A 股代码（如 "600519"）
            request_type: 用户请求描述

        Returns:
            包含子任务的 AnalysisPipeline
        """
        pipeline = self.create_pipeline(stock_code)

        # 判断任务类型，自动选择 Agent
        primary_agent = route_task(request_type)

        # 添加主任务
        main_task_id = pipeline.add_task(primary_agent, request_type, priority=1)

        # 如果涉及估值，自动添加 comps 并行任务
        if any(kw in request_type for kw in ["估值", "DCF", "LBO", "comps", "对标"]):
            # comps 可以并行执行（不依赖主任务）
            comps_task = pipeline.add_task(
                AgentName.PITCH_AGENT,
                f"为 {stock_code} 构建可比公司估值（PE/PB/PS）",
                priority=2,
            )
            # DCF 依赖 comps 完成
            pipeline.add_task(
                AgentName.MODEL_BUILDER,
                f"为 {stock_code} 构建 DCF 估值模型",
                depends_on=[main_task_id],
                priority=1,
            )

        # 如果涉及财报分析，自动添加财报前瞻
        if any(kw in request_type for kw in ["财报", "业绩", "earnings"]):
            pipeline.add_task(
                AgentName.EARNINGS_REVIEWER,
                f"分析 {stock_code} 最新财报，对比一致预期",
                priority=2,
            )

        return pipeline

    @staticmethod
    def compute_execution_order(pipeline: AnalysisPipeline) -> list[list[str]]:
        """
        根据依赖关系计算执行批次。
        返回批次列表，每批次内的任务可并行执行。
        """
        # 构建依赖图
        task_map = {f"task_{i}": req for i, req in enumerate(pipeline.requests)}
        in_degree: dict[str, int] = {tid: 0 for tid in task_map}
        dependents: dict[str, list[str]] = {tid: [] for tid in task_map}

        for tid, req in task_map.items():
            for dep in req.depends_on:
                if dep in task_map:
                    in_degree[tid] += 1
                    dependents[dep].append(tid)

        # Kahn 算法拓扑排序
        batches: list[list[str]] = []
        ready = [tid for tid, deg in in_degree.items() if deg == 0]

        while ready:
            batches.append(sorted(ready))  # 排序保证确定性
            next_ready = []
            for tid in ready:
                for dep_tid in dependents[tid]:
                    in_degree[dep_tid] -= 1
                    if in_degree[dep_tid] == 0:
                        next_ready.append(dep_tid)
            ready = next_ready

        # 检测环
        total = len(task_map)
        counted = sum(len(b) for b in batches)
        if counted < total:
            raise ValueError(
                f"任务依赖环检测到: {counted}/{total} 任务已排期"
            )

        return batches

    @staticmethod
    def merge_results(
        pipeline: AnalysisPipeline,
        batched_results: list[list[TaskResult]],
    ) -> dict[str, Any]:
        """合并所有 Agent 输出，返回结构化结果。"""
        merged: dict[str, Any] = {
            "stock_code": pipeline.stock_code,
            "total_time": time.time() - pipeline.started_at,
            "agents_involved": set(),
            "data_sources": set(),
            "outputs": {},
            "warnings": [],
        }

        for batch in batched_results:
            for result in batch:
                merged["agents_involved"].add(result.agent.value)
                merged["data_sources"].add(result.data_source_used.value)
                merged["outputs"][result.task_id] = {
                    "agent": result.agent.value,
                    "success": result.error is None,
                    "output": result.output,
                }
                if result.error:
                    merged["warnings"].append(
                        f"{result.task_id} ({result.agent.value}): {result.error}"
                    )

        # 转换为列表以便 JSON 序列化
        merged["agents_involved"] = list(merged["agents_involved"])
        merged["data_sources"] = list(merged["data_sources"])
        return merged
