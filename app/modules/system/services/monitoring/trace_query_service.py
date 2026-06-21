from __future__ import annotations
"""Service for querying execution trace logs.

Note: This is a lightweight fallback for the UI "观测台" page. It scans the
application log for TraceID occurrences and extracts structured SQL trace lines
when possible.
"""


import re
from pathlib import Path
from typing import Any


class TraceQueryService:
    """Query trace-related entries from local log files."""

    def __init__(self, log_paths: list[str] | None = None):
        self.log_paths = [Path(p) for p in (log_paths or ["instance/app.log", "logs/app.log"])]

    def _pick_existing_log(self) -> Path | None:
        for p in self.log_paths:
            if p.exists():
                return p
        return None

    def get_traces_by_id(self, trace_id: str) -> list[dict[str, Any]]:
        """Parse local log to find entries related to a trace id."""
        traces: list[dict[str, Any]] = []
        log_path = self._pick_existing_log()
        if log_path is None:
            return traces

        pattern = re.compile(
            r"\[SQL_TRACE\]\s*Time:\s*(?P<time>[\d\.]+)ms\s*\|\s*TraceID:\s*(?P<trace_id>.*?)\s*\|\s*Query:\s*(?P<query>.*)"
        )

        with log_path.open("r", encoding="utf-8") as f:
            for line in f:
                if trace_id not in line:
                    continue
                match = pattern.search(line)
                if match:
                    traces.append(match.groupdict())
                else:
                    traces.append({"raw": line.strip()})
        return traces
