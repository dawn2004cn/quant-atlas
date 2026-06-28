from __future__ import annotations
"""Workspace memory: shared state across tool calls within a single run.

Ported from Vibe-Trading.
"""


from dataclasses import dataclass, field


@dataclass
class WorkspaceMemory:
    """Shared workspace state between tools during a single agent run."""

    run_dir: str | None = None
    counters: dict[str, int] = field(default_factory=dict)

    def increment(self, key: str) -> int:
        self.counters[key] = self.counters.get(key, 0) + 1
        return self.counters[key]

    def to_summary(self) -> str:
        lines: list[str] = []
        if self.run_dir:
            lines.append(f"- run_dir: {self.run_dir}")
        if self.counters:
            counter_parts = [f"{k}={v}" for k, v in self.counters.items()]
            lines.append(f"- counters: {', '.join(counter_parts)}")
        return "\n".join(lines) if lines else "(empty state)"
