from __future__ import annotations

"""File store for team workflows and run history."""

import json
import logging
from pathlib import Path
from typing import Any

from app.domain.team_workflow_schema import TeamWorkflowDescriptor

logger = logging.getLogger(__name__)


class TeamWorkflowStore:
    """Persist team workflows and execution runs under instance/team_workflows/."""

    def __init__(self, base_dir: Path | str | None = None) -> None:
        from app.config import BASE_DIR

        self._dir = Path(base_dir or BASE_DIR / "instance" / "team_workflows")
        self._dir.mkdir(parents=True, exist_ok=True)

    def _workflow_path(self, team_id: int, workflow_id: str) -> Path:
        safe = "".join(ch for ch in workflow_id if ch.isalnum() or ch in "-_")
        return self._dir / f"team_{team_id}_{safe}.json"

    def _runs_path(self, team_id: int) -> Path:
        return self._dir / f"team_{team_id}_runs.jsonl"

    def save_workflow(self, team_id: int, workflow: TeamWorkflowDescriptor) -> TeamWorkflowDescriptor:
        wf = workflow.model_copy(update={"team_id": team_id})
        path = self._workflow_path(team_id, wf.id)
        path.write_text(wf.model_dump_json(indent=2), encoding="utf-8")
        return wf

    def get_workflow(self, team_id: int, workflow_id: str) -> TeamWorkflowDescriptor | None:
        path = self._workflow_path(team_id, workflow_id)
        if not path.exists():
            return None
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            return TeamWorkflowDescriptor.model_validate(raw)
        except Exception as exc:
            logger.warning("team_workflow_store.get: %s", exc)
            return None

    def list_workflows(self, team_id: int) -> list[dict[str, Any]]:
        prefix = f"team_{team_id}_"
        items: list[dict[str, Any]] = []
        for path in sorted(self._dir.glob(f"{prefix}*.json")):
            if path.name.endswith("_runs.jsonl") or "_runs" in path.stem:
                continue
            try:
                raw = json.loads(path.read_text(encoding="utf-8"))
                items.append(
                    {
                        "id": raw.get("id"),
                        "name": raw.get("name"),
                        "description": raw.get("description", ""),
                        "node_count": len(raw.get("nodes") or []),
                    }
                )
            except Exception:
                continue
        return items

    def append_run(self, team_id: int, run: dict[str, Any]) -> None:
        line = json.dumps(run, ensure_ascii=False)
        with self._runs_path(team_id).open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")

    def update_run(self, team_id: int, run_id: str, patch: dict[str, Any]) -> dict[str, Any] | None:
        path = self._runs_path(team_id)
        if not path.exists():
            return None
        lines = path.read_text(encoding="utf-8").splitlines()
        updated: dict[str, Any] | None = None
        out_lines: list[str] = []
        for line in lines:
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                out_lines.append(line)
                continue
            if str(row.get("run_id")) == run_id:
                row.update(patch)
                updated = row
                out_lines.append(json.dumps(row, ensure_ascii=False))
            else:
                out_lines.append(line)
        if updated is not None:
            path.write_text("\n".join(out_lines) + ("\n" if out_lines else ""), encoding="utf-8")
        return updated

    def get_run(self, team_id: int, run_id: str) -> dict[str, Any] | None:
        for row in self.list_runs(team_id, limit=500):
            if str(row.get("run_id")) == run_id:
                return row
        return None

    def list_runs(self, team_id: int, *, limit: int = 40) -> list[dict[str, Any]]:
        path = self._runs_path(team_id)
        if not path.exists():
            return []
        rows: list[dict[str, Any]] = []
        try:
            for line in path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        except Exception as exc:
            logger.warning("team_workflow_store.list_runs: %s", exc)
            return []
        rows.sort(key=lambda r: str(r.get("created_at") or ""), reverse=True)
        return rows[:limit]
