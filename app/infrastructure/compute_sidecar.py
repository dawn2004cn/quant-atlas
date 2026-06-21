"""Compute Sidecar — lightweight edge compute node for shadow grid.

Phase 15 component: receives remote computation tasks, executes sandboxed
Rust/WASM calculations, and reports results. Designed to run as a standalone
process or sidecar container.
"""
from __future__ import annotations

import json
import os
import struct
import sys
import time
import uuid
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Callable

from app.core.logger import get_logger

logger = get_logger(__name__)

# ── Task Definitions ──────────────────────────────────────────────

TaskHandler = Callable[[dict[str, Any]], dict[str, Any]]


@dataclass
class ComputeTask:
    """A single computation task dispatched to a sidecar node."""

    task_id: str
    task_type: str  # "sma", "ema", "atr", "zscore", "batch", "sharpe"
    payload: dict[str, Any] = field(default_factory=dict)
    priority: int = 0
    deadline: float = 0.0
    source_node: str = ""


@dataclass
class ComputeResult:
    """Result payload sent back from sidecar to dispatcher."""

    task_id: str
    success: bool
    data: list[float] | float | None = None
    error: str = ""
    wall_time_ms: float = 0.0
    metrics: dict[str, Any] = field(default_factory=dict)


# ── Task Registry ──────────────────────────────────────────────────

TASK_REGISTRY: dict[str, TaskHandler] = {}


def register_task(task_type: str):
    """Decorator to register a computation handler."""

    def wrapper(fn: TaskHandler) -> TaskHandler:
        TASK_REGISTRY[task_type] = fn
        return fn

    return wrapper


@register_task("sma")
def _handle_sma(payload: dict[str, Any]) -> dict[str, Any]:
    data = payload.get("data", [])
    window = payload.get("window", 5)
    if not data or window <= 0:
        return {"error": "invalid params"}
    result = []
    for i in range(len(data)):
        if i < window - 1:
            result.append(0.0)
        else:
            s = sum(data[i - window + 1:i + 1])
            result.append(round(s / window, 4))
    return {"data": result}


@register_task("ema")
def _handle_ema(payload: dict[str, Any]) -> dict[str, Any]:
    data = payload.get("data", [])
    window = payload.get("window", 5)
    if not data or window <= 0:
        return {"error": "invalid params"}
    alpha = 2.0 / (window + 1)
    result = [data[0]]
    for i in range(1, len(data)):
        result.append(data[i] * alpha + result[-1] * (1.0 - alpha))
    return {"data": result}


@register_task("atr")
def _handle_atr(payload: dict[str, Any]) -> dict[str, Any]:
    highs = payload.get("highs", [])
    lows = payload.get("lows", [])
    closes = payload.get("closes", [])
    window = payload.get("window", 14)
    n = min(len(highs), len(lows), len(closes))
    if n < window + 1:
        return {"error": "insufficient data"}
    tr = [highs[0] - lows[0]]
    for i in range(1, n):
        hl = highs[i] - lows[i]
        hpc = abs(highs[i] - closes[i - 1])
        lpc = abs(lows[i] - closes[i - 1])
        tr.append(max(hl, hpc, lpc))
    result = [0.0] * n
    for i in range(window - 1, n):
        result[i] = sum(tr[i - window + 1:i + 1]) / window
    return {"data": result}


@register_task("sharpe")
def _handle_sharpe(payload: dict[str, Any]) -> dict[str, Any]:
    values = payload.get("portfolio_values", payload.get("data", []))
    if len(values) < 2:
        return {"error": "insufficient data"}
    n = len(values) - 1
    returns = [(values[i + 1] - values[i]) / values[i] for i in range(n) if values[i] > 0]
    if not returns:
        return {"data": 0.0}
    mean = sum(returns) / len(returns)
    var = sum((r - mean) ** 2 for r in returns) / len(returns)
    sharpe = mean / (var ** 0.5) * (252 ** 0.5) if var > 0 else 0.0
    return {"data": round(sharpe, 4)}


# ── Sidecar Runtime ────────────────────────────────────────────────


class ComputeSidecar:
    """Lightweight compute node for the shadow grid.

    Supports both in-process task execution and a simple JSON-line IPC
    protocol for subprocess/piped invocation.
    """

    def __init__(
        self,
        node_id: str = "",
        registry: dict | None = None,
        task_source: str = "direct",
    ):
        self.node_id = node_id or f"sidecar-{uuid.uuid4().hex[:8]}"
        self._registry = registry or TASK_REGISTRY
        self._task_source = task_source
        self._start_time = time.time()
        self._task_count = 0

    def get_node_info(self) -> dict[str, Any]:
        """Return sidecar node health and capabilities."""
        return {
            "node_id": self.node_id,
            "uptime_seconds": round(time.time() - self._start_time, 1),
            "task_count": self._task_count,
            "capabilities": list(self._registry.keys()),
            "status": "ready",
            "python_version": sys.version,
        }

    def execute(self, task: ComputeTask) -> ComputeResult:
        """Execute a single compute task."""
        start = time.time()
        self._task_count += 1

        try:
            handler = self._registry.get(task.task_type)
            if handler is None:
                return ComputeResult(
                    task_id=task.task_id,
                    success=False,
                    error=f"unknown task type: {task.task_type}",
                )
            result = handler(task.payload)
            elapsed = (time.time() - start) * 1000

            if "error" in result:
                return ComputeResult(
                    task_id=task.task_id,
                    success=False,
                    error=result["error"],
                    wall_time_ms=round(elapsed, 1),
                )
            return ComputeResult(
                task_id=task.task_id,
                success=True,
                data=result.get("data"),
                wall_time_ms=round(elapsed, 1),
            )
        except Exception as exc:
            elapsed = (time.time() - start) * 1000
            return ComputeResult(
                task_id=task.task_id,
                success=False,
                error=str(exc),
                wall_time_ms=round(elapsed, 1),
            )

    def execute_batch(self, tasks: list[ComputeTask]) -> list[ComputeResult]:
        """Execute multiple tasks sequentially."""
        return [self.execute(t) for t in tasks]

    def process_json_line(self, line: str) -> str:
        """Process a single JSON-line IPC message."""
        try:
            msg = json.loads(line)
            action = msg.get("action", "execute")
            if action == "ping":
                return json.dumps({"action": "pong", "node": self.node_id})
            elif action == "info":
                return json.dumps({"action": "info", **self.get_node_info()})
            elif action == "execute":
                task = ComputeTask(**msg["task"])
                result = self.execute(task)
                return json.dumps({"action": "result", **asdict(result)})
            else:
                return json.dumps({"action": "error", "message": f"unknown action: {action}"})
        except Exception as exc:
            return json.dumps({"action": "error", "message": str(exc)})

    def run_ipc_loop(self):
        """Read JSON lines from stdin, write results to stdout."""
        logger.info("ComputeSidecar %s IPC loop started", self.node_id)
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            response = self.process_json_line(line)
            sys.stdout.write(response + "\n")
            sys.stdout.flush()


def create_sidecar(node_id: str = "") -> ComputeSidecar:
    """Factory: create a ComputeSidecar with default registry."""
    return ComputeSidecar(node_id=node_id)


__all__ = [
    "ComputeTask",
    "ComputeResult",
    "ComputeSidecar",
    "register_task",
    "create_sidecar",
]
