from __future__ import annotations

"""RD-Agent 异步任务状态（文件落盘，便于无 Redis 时查询进度）。"""


import json
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


class RDAgentJobStore:
    def __init__(self, base_dir: Path) -> None:
        root = Path(base_dir) / "config" / "rdagent_jobs"
        root.parent.mkdir(parents=True, exist_ok=True)
        legacy = Path(base_dir) / "instance" / "rdagent_jobs"
        if not root.exists() and legacy.is_dir():
            shutil.move(str(legacy), str(root))
        self._root = root

    def _path(self, job_id: str) -> Path:
        return self._root / f"{job_id}.json"

    def create(self, *, params_summary: dict[str, Any] | None = None) -> str:
        job_id = str(uuid.uuid4())
        self._root.mkdir(parents=True, exist_ok=True)
        data: dict[str, Any] = {
            "id": job_id,
            "status": "queued",
            "progress": 0,
            "message": "queued",
            "created_at": _utc_now(),
            "updated_at": _utc_now(),
            "params_summary": params_summary or {},
            "result": None,
            "error": None,
        }
        self._write(self._path(job_id), data)
        return job_id

    def update(self, job_id: str, **kwargs: Any) -> None:
        p = self._path(job_id)
        if not p.is_file():
            return
        data = json.loads(p.read_text(encoding="utf-8"))
        data.update(kwargs)
        data["updated_at"] = _utc_now()
        self._write(p, data)

    def get(self, job_id: str) -> dict[str, Any] | None:
        p = self._path(job_id)
        if not p.is_file():
            return None
        return json.loads(p.read_text(encoding="utf-8"))

    @staticmethod
    def _write(path: Path, data: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
