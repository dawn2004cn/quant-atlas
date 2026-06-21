"""IntentDecomposer — fuzzy intent → ordered ExecutionPlan."""
from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Any

from app.core.logger import get_logger
from app.domain.intent_decomposer import (
    ExecutionPlan,
    ExecutionStep,
    StepStatus,
    StepType,
)

logger = get_logger(__name__)

_INTENT_PATTERNS: dict[str, list[dict[str, Any]]] = {
    "复盘亏损策略": [
        {"type": StepType.FETCH_DATA, "label": "拉取策略绩效", "description": "获取近期策略回测/实盘结果"},
        {"type": StepType.CALCULATE, "label": "计算亏损归因", "description": "按策略维度聚合亏损额与回撤"},
        {"type": StepType.ARBITER_REVIEW, "label": "仲裁复盘", "description": "MetaArbiter 复盘失败原因"},
        {"type": StepType.OPTIMIZE, "label": "生成改进建议", "description": "基于复盘结果输出优化方向"},
        {"type": StepType.NOTIFY, "label": "推送报告", "description": "将结论写入 DecisionContext 并通知用户"},
    ],
    "因子挖掘": [
        {"type": StepType.FETCH_DATA, "label": "拉取行情与因子库", "description": "获取基础行情与现有因子集"},
        {"type": StepType.CALCULATE, "label": "计算候选因子", "description": "基于 RD-Agent / 规则库生成候选 Alpha"},
        {"type": StepType.ARBITER_REVIEW, "label": "因子初筛", "description": "IC/IR 门禁筛选"},
        {"type": StepType.STORE, "label": "存入因子库", "description": "将合格因子持久化"},
    ],
    "默认": [
        {"type": StepType.FETCH_DATA, "label": "理解意图", "description": "解析用户输入并确定标的"},
        {"type": StepType.CALCULATE, "label": "执行分析", "description": "调用对应分析引擎"},
        {"type": StepType.NOTIFY, "label": "输出结果", "description": "返回结论"},
    ],
}


def _match_intent(text: str) -> str:
    t = text.lower()
    if any(k in t for k in ("复盘", "亏损", "改进", "优化")) and any(k in t for k in ("策略", "回测")):
        return "复盘亏损策略"
    if any(k in t for k in ("因子", "alpha", "挖掘", "特征")):
        return "因子挖掘"
    return "默认"


class IntentDecomposer:
    """Decompose free-text intent into ordered ExecutionPlan."""

    def decompose(self, text: str, *, symbol: str = "", market: str = "ALL") -> ExecutionPlan:
        intent_key = _match_intent(text)
        steps_cfg = _INTENT_PATTERNS.get(intent_key, _INTENT_PATTERNS["默认"])
        steps: list[ExecutionStep] = []
        for idx, cfg in enumerate(steps_cfg):
            sid = f"step-{uuid.uuid4().hex[:8]}"
            steps.append(
                ExecutionStep(
                    step_id=sid,
                    step_type=StepType(cfg["type"]),
                    label=cfg["label"],
                    description=cfg["description"],
                    params={"order": idx, "symbol": symbol, "market": market},
                )
            )
        return ExecutionPlan(
            plan_id=f"plan-{uuid.uuid4().hex[:12]}",
            intent=intent_key,
            symbol=symbol,
            market=market,
            steps=steps,
            metadata={"source_text": text},
        )
