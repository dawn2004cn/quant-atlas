from __future__ import annotations

"""Redis 分布式追踪 span 类型与数据结构。"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class SpanType(str, Enum):
    """Type of tracing span."""

    AGENT_DECISION = "agent_decision"
    DATA_FETCH = "data_fetch"
    RD_AGENT_RUN = "rd_agent_run"
    BACKTEST = "backtest"
    DRIFT_CHECK = "drift_check"
    SHADOW_TEST = "shadow_test"
    HOT_SWAP = "hot_swap"
    ORDER_EXECUTION = "order_execution"


@dataclass
class TraceSpan:
    """Single trace span."""

    span_id: str
    trace_id: str
    span_type: str
    operation: str
    start_time: str
    end_time: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
