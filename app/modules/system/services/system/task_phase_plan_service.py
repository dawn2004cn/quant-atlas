from __future__ import annotations

"""Resolve user-facing phase plans for long-running tasks."""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class TaskPhase:
    key: str
    label: str
    description: str
    weight: int


DEFAULT_PHASES: tuple[TaskPhase, ...] = (
    TaskPhase("queued", "Queued", "Task accepted and waiting for a worker.", 5),
    TaskPhase("running", "Running", "Worker is processing the request.", 90),
    TaskPhase("finished", "Finished", "Result is ready or the task has ended.", 5),
)

PHASE_TEMPLATES: tuple[tuple[tuple[str, ...], tuple[TaskPhase, ...]], ...] = (
    (
        ("factor", "ic", "rdagent", "alpha"),
        (
            TaskPhase("prepare", "Prepare factor universe", "Load symbols, dates and baseline data.", 20),
            TaskPhase("compute", "Compute factors", "Run factor expressions and feature jobs.", 35),
            TaskPhase("evaluate", "Evaluate IC", "Measure IC, decay and stability.", 30),
            TaskPhase("publish", "Publish findings", "Store metrics and emit alerts.", 15),
        ),
    ),
    (
        ("research", "yanbao", "news", "headline"),
        (
            TaskPhase("collect", "Collect evidence", "Fetch reports, news and raw source material.", 35),
            TaskPhase("enrich", "Enrich signals", "Tag sentiment, symbols and relevance.", 35),
            TaskPhase("archive", "Archive evidence", "Persist searchable evidence records.", 20),
            TaskPhase("notify", "Notify UI", "Publish summary and task messages.", 10),
        ),
    ),
    (
        ("sync", "backfill", "history", "tdx", "qlib", "market_data"),
        (
            TaskPhase("fetch", "Fetch market data", "Download or read source market rows.", 40),
            TaskPhase("normalize", "Normalize records", "Map source fields into internal schema.", 20),
            TaskPhase("persist", "Persist snapshot", "Write rows and indexes to storage.", 25),
            TaskPhase("verify", "Verify coverage", "Check date range and missing symbols.", 15),
        ),
    ),
    (
        ("strategy", "snapshot", "backtest", "slippage", "execution"),
        (
            TaskPhase("load", "Load strategy context", "Load config, positions and market facts.", 25),
            TaskPhase("simulate", "Simulate scenario", "Run scoring, replay or execution analysis.", 45),
            TaskPhase("compare", "Compare baseline", "Measure delta against benchmark or previous run.", 20),
            TaskPhase("save", "Save result", "Persist snapshot and UI summary.", 10),
        ),
    ),
)


class TaskPhasePlanService:
    """Turn task names and states into stable phase metadata."""

    def resolve_phases(
        self,
        *,
        task_name: str | None = None,
        estimated_steps: list[str] | None = None,
    ) -> tuple[list[TaskPhase], str]:
        if estimated_steps:
            return (
                [
                    TaskPhase(
                        key=f"custom_{idx}",
                        label=label,
                        description=label,
                        weight=max(1, round(100 / max(len(estimated_steps), 1))),
                    )
                    for idx, label in enumerate(estimated_steps)
                ],
                "request",
            )

        haystack = str(task_name or "").lower()
        for needles, phases in PHASE_TEMPLATES:
            if any(needle in haystack for needle in needles):
                return list(phases), "template"
        return list(DEFAULT_PHASES), "default"

    def build_progress(
        self,
        *,
        task_name: str | None = None,
        estimated_steps: list[str] | None = None,
        progress: dict[str, Any] | None = None,
        state: str = "PENDING",
    ) -> dict[str, Any]:
        phases, source = self.resolve_phases(task_name=task_name, estimated_steps=estimated_steps)
        stored_steps = (progress or {}).get("steps")
        if stored_steps:
            phases, source = self.resolve_phases(
                task_name=task_name,
                estimated_steps=[str(step) for step in stored_steps],
            )
            source = "progress"

        step_index = int((progress or {}).get("step_index") or 0)
        if state == "SUCCESS":
            step_index = len(phases) - 1
        step_index = max(0, min(step_index, max(len(phases) - 1, 0)))

        percent = (progress or {}).get("percent")
        if percent is None:
            percent = self._percent_for(step_index, phases, state)
        if state == "SUCCESS":
            percent = 100.0

        current = phases[step_index] if phases else None
        next_phase = phases[step_index + 1] if step_index + 1 < len(phases) else None
        return {
            "steps": [phase.label for phase in phases],
            "step_details": [
                {
                    "key": phase.key,
                    "label": phase.label,
                    "description": phase.description,
                    "weight": phase.weight,
                }
                for phase in phases
            ],
            "step_index": step_index,
            "percent": float(percent),
            "current_step": current.label if current else "",
            "current_step_key": current.key if current else "",
            "next_step": next_phase.label if next_phase else "",
            "phase_source": source,
        }

    @staticmethod
    def _percent_for(step_index: int, phases: list[TaskPhase], state: str) -> float:
        if not phases:
            return 0.0
        if state == "PENDING":
            return 0.0
        done_weight = sum(phase.weight for phase in phases[:step_index])
        current_weight = phases[step_index].weight * 0.5
        total = max(sum(phase.weight for phase in phases), 1)
        return round(min(99.0, (done_weight + current_weight) / total * 100.0), 1)


__all__ = ["TaskPhasePlanService", "TaskPhase", "DEFAULT_PHASES", "PHASE_TEMPLATES"]
