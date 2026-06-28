from __future__ import annotations
"""RD 成功注册后，将 ``factor_task`` 条目追加到 ``config/factor_catalog/autopublish.jsonl``（按 artifact_id 去重）。"""


import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


from ...core.logger import get_logger
from .artifact_registry import RDAgentArtifactRegistry



logger = get_logger(__name__)

def _existing_artifact_ids(path: Path) -> set[str]:
    if not path.is_file():
        return set()
    ids: set[str] = set()
    try:
        with path.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                aid = str(row.get("artifact_id") or "").strip()
                if aid:
                    ids.add(aid)
    except OSError as exc:
        logger.warning("factor_catalog_export read existing: %s", exc)
    return ids


def append_factor_tasks_from_bundle(*, base_dir: Path, run_id: str) -> dict[str, Any]:
    """从已写入的 bundle 导出 ``factor_task``；重复 ``artifact_id`` 跳过。"""
    reg = RDAgentArtifactRegistry(base_dir)
    bundle = reg.get_run_bundle(run_id)
    if not bundle:
        return {"ok": False, "skipped": True, "message": "bundle 不存在", "appended": 0}

    root = Path(base_dir) / "config" / "factor_catalog"
    root.mkdir(parents=True, exist_ok=True)
    path = root / "autopublish.jsonl"
    existing = _existing_artifact_ids(path)
    ts = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    appended = 0
    lines: list[str] = []

    for a in bundle.get("artifacts") or []:
        if not isinstance(a, dict) or a.get("kind") != "factor_task":
            continue
        aid = str(a.get("artifact_id") or "").strip()
        if not aid or aid in existing:
            continue
        row = {
            "exported_at": ts,
            "run_id": run_id,
            "artifact_id": aid,
            "round_index": a.get("round_index"),
            "factor_name": a.get("factor_name"),
            "factor_formulation": (str(a.get("factor_formulation") or ""))[:8000],
            "factor_description": (str(a.get("factor_description") or ""))[:2000],
            "metrics": a.get("metrics") if isinstance(a.get("metrics"), dict) else {},
            "provider_uri": bundle.get("provider_uri"),
            "benchmark": bundle.get("benchmark"),
        }
        lines.append(json.dumps(row, ensure_ascii=False) + "\n")
        existing.add(aid)
        appended += 1

    if lines:
        try:
            with path.open("a", encoding="utf-8") as f:
                f.writelines(lines)
        except OSError as exc:
            logger.warning("factor_catalog_export append failed: %s", exc)
            return {"ok": False, "message": str(exc), "appended": 0}
        logger.info("factor_catalog_export run_id=%s appended=%d", run_id, appended)

    return {"ok": True, "appended": appended, "path": str(path.resolve())}
