from __future__ import annotations

"""RD-Agent 运行产物注册：供回测/选股消费的可查询清单（文件注册表，可后续换 SQLite）。"""


import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.core.key_encryption import decrypt, encrypt
from app.core.logger import get_logger

logger = get_logger(__name__)


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


class RDAgentArtifactRegistry:
    """``config/rdagent_registry/runs/{run_id}.json`` + ``registry_index.json``。"""

    def __init__(self, base_dir: Path) -> None:
        self._base = Path(base_dir)
        self._root = self._base / "config" / "rdagent_registry"
        self._root.parent.mkdir(parents=True, exist_ok=True)
        legacy = self._base / "instance" / "rdagent_registry"
        if not self._root.exists() and legacy.is_dir():
            shutil.move(str(legacy), str(self._root))
            logger.info("rdagent: migrated artifact registry %s -> %s", legacy, self._root)
        self._runs = self._root / "runs"
        self._index_path = self._root / "registry_index.json"

    def register_from_result(self, run_id: str, result: dict[str, Any]) -> list[dict[str, Any]]:
        """从 ``run_factor_mining_loop`` 返回的 ``report.rounds`` 抽取因子表达式/代码与指标摘要。"""
        artifacts: list[dict[str, Any]] = []
        report = result.get("report") or {}
        rounds = report.get("rounds") or []

        for ri, rnd in enumerate(rounds):
            metrics = rnd.get("qlib_metrics_series") or {}
            for ti, task in enumerate(rnd.get("tasks") or []):
                fid = task.get("factor_name") or f"round{ri}_task{ti}"
                artifacts.append(
                    {
                        "artifact_id": f"{run_id}::r{ri}::task::{fid}",
                        "version": 1,
                        "kind": "factor_task",
                        "round_index": ri,
                        "factor_name": task.get("factor_name"),
                        "factor_formulation": encrypt(task.get("factor_formulation") or ""),
                        "factor_description": encrypt(task.get("factor_description") or ""),
                        "metrics": metrics,
                    }
                )
            for ci, code in enumerate(rnd.get("code_snippets") or []):
                fn = code.get("file") or f"snippet_{ci}"
                artifacts.append(
                    {
                        "artifact_id": f"{run_id}::r{ri}::code::{fn}",
                        "version": 1,
                        "kind": "factor_code",
                        "round_index": ri,
                        "file": fn,
                        "code_preview": encrypt((code.get("snippet") or "")[:8000]),
                    }
                )

        bundle = {
            "run_id": run_id,
            "registered_at": _utc(),
            "ok": result.get("ok"),
            "provider_uri": result.get("provider_uri"),
            "market": result.get("market"),
            "benchmark": result.get("benchmark"),
            "loop_n": result.get("loop_n"),
            "artifacts": artifacts,
            "round_count": report.get("round_count", len(rounds)),
        }

        self._runs.mkdir(parents=True, exist_ok=True)
        run_path = self._runs / f"{run_id}.json"
        run_path.write_text(json.dumps(bundle, ensure_ascii=False, indent=2), encoding="utf-8")
        self._upsert_index(run_id, len(artifacts), bundle["registered_at"], ok=bool(result.get("ok")))
        logger.info("rdagent artifacts registered run_id=%s count=%d", run_id, len(artifacts))
        return artifacts

    def _upsert_index(self, run_id: str, count: int, ts: str, *, ok: bool) -> None:
        entries: list[dict[str, Any]] = []
        if self._index_path.is_file():
            try:
                entries = json.loads(self._index_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                entries = []
        if not isinstance(entries, list):
            entries = []
        filtered = [e for e in entries if e.get("run_id") != run_id]
        filtered.append(
            {
                "run_id": run_id,
                "artifact_count": count,
                "registered_at": ts,
                "ok": ok,
            }
        )
        filtered.sort(key=lambda x: x.get("registered_at") or "", reverse=True)
        self._root.mkdir(parents=True, exist_ok=True)
        self._index_path.write_text(json.dumps(filtered[:500], ensure_ascii=False, indent=2), encoding="utf-8")

    def merge_qlib_gate(self, run_id: str, gate: dict[str, Any]) -> None:
        """将门禁结果写入 ``runs/{run_id}.json`` 的 ``qlib_gate``，并同步索引摘要字段。"""
        p = self._runs / f"{run_id}.json"
        if not p.is_file():
            logger.warning("merge_qlib_gate: missing bundle %s", run_id)
            return
        try:
            bundle = json.loads(p.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            logger.warning("merge_qlib_gate: corrupt bundle %s", run_id)
            return
        payload = dict(gate)
        payload["checked_at"] = _utc()
        bundle["qlib_gate"] = payload
        p.write_text(json.dumps(bundle, ensure_ascii=False, indent=2), encoding="utf-8")
        self._patch_index(
            run_id,
            {
                "qlib_gate_ok": payload.get("ok"),
                "qlib_gate_skipped": payload.get("skipped"),
            },
        )
        logger.info("rdagent qlib_gate merged run_id=%s ok=%s", run_id, payload.get("ok"))

    def _patch_index(self, run_id: str, patch: dict[str, Any]) -> None:
        if not self._index_path.is_file():
            return
        try:
            entries = json.loads(self._index_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return
        if not isinstance(entries, list):
            return
        for e in entries:
            if isinstance(e, dict) and e.get("run_id") == run_id:
                e.update(patch)
                break
        self._index_path.write_text(json.dumps(entries[:500], ensure_ascii=False, indent=2), encoding="utf-8")

    def _decrypt_artifacts(self, bundle: dict[str, Any]) -> dict[str, Any]:
        bundle = dict(bundle)
        for a in bundle.get("artifacts") or []:
            for field in ("factor_formulation", "factor_description"):
                if a.get(field):
                    try:
                        a[field] = decrypt(a[field])
                    except Exception:
                        logger.debug("Decryption failed for artifact field=%s", field)
            if a.get("code_preview"):
                try:
                    a["code_preview"] = decrypt(a["code_preview"])
                except Exception:
                    logger.debug("Decryption failed for artifact code_preview")
        return bundle

    def get_run_bundle(self, run_id: str) -> dict[str, Any] | None:
        p = self._runs / f"{run_id}.json"
        if not p.is_file():
            return None
        try:
            return self._decrypt_artifacts(json.loads(p.read_text(encoding="utf-8")))
        except Exception:
            return None

    def list_artifact_summaries(self, run_id: str) -> list[dict[str, Any]]:
        bundle = self.get_run_bundle(run_id)
        if not bundle:
            return []
        out: list[dict[str, Any]] = []
        for a in bundle.get("artifacts") or []:
            out.append(
                {
                    "artifact_id": a.get("artifact_id"),
                    "kind": a.get("kind"),
                    "version": a.get("version"),
                    "factor_name": a.get("factor_name"),
                    "file": a.get("file"),
                }
            )
        return out

    def list_registry_index(self, *, limit: int = 100) -> list[dict[str, Any]]:
        if not self._index_path.is_file():
            return []
        try:
            data = json.loads(self._index_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return []
        if isinstance(data, list):
            return data[:limit]
        return []
