from __future__ import annotations

"""TDX 全量同步检查点：失败列表落盘、续跑跳过已成功代码。"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.config import INSTANCE_DIR
from app.core.logger import get_logger
from app.domain.shared.symbol_normalizer import SymbolNormalizer

logger = get_logger(__name__)

DEFAULT_CHECKPOINT_DIR = INSTANCE_DIR / "tdx_sync"
FAILED_CODES_FILE = "failed_codes.txt"
OK_CODES_FILE = "ok_codes.txt"
LAST_RUN_FILE = "last_run.json"


def checkpoint_dir() -> Path:
    return DEFAULT_CHECKPOINT_DIR


def failed_codes_path(base: Path | None = None) -> Path:
    return (base or checkpoint_dir()) / FAILED_CODES_FILE


def ok_codes_path(base: Path | None = None) -> Path:
    return (base or checkpoint_dir()) / OK_CODES_FILE


def last_run_path(base: Path | None = None) -> Path:
    return (base or checkpoint_dir()) / LAST_RUN_FILE


def ensure_checkpoint_dir(base: Path | None = None) -> Path:
    d = base or checkpoint_dir()
    d.mkdir(parents=True, exist_ok=True)
    return d


def load_code_lines(path: Path) -> list[str]:
    if not path.is_file():
        return []
    out: list[str] = []
    seen: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        code = SymbolNormalizer.normalize_cn_symbol(line.strip())
        if not code or code in seen:
            continue
        seen.add(code)
        out.append(code)
    return out


def load_failed_codes(base: Path | None = None, *, file: Path | str | None = None) -> list[str]:
    if file is not None:
        return load_code_lines(Path(file))
    return load_code_lines(failed_codes_path(base))


def load_ok_codes(base: Path | None = None) -> list[str]:
    return load_code_lines(ok_codes_path(base))


def append_ok_codes(codes: list[str], base: Path | None = None) -> None:
    if not codes:
        return
    d = ensure_checkpoint_dir(base)
    p = d / OK_CODES_FILE
    existing = set(load_ok_codes(d))
    with p.open("a", encoding="utf-8") as fh:
        for c in codes:
            norm = SymbolNormalizer.normalize_cn_symbol(c)
            if norm and norm not in existing:
                fh.write(norm + "\n")
                existing.add(norm)


def write_failed_codes(
    failed: list[dict[str, Any]],
    base: Path | None = None,
) -> Path:
    d = ensure_checkpoint_dir(base)
    p = d / FAILED_CODES_FILE
    lines: list[str] = []
    seen: set[str] = set()
    for item in failed:
        code = SymbolNormalizer.normalize_cn_symbol(str(item.get("code", "")))
        if not code or code in seen:
            continue
        seen.add(code)
        lines.append(code)
    p.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
    return p


def save_last_run(
    payload: dict[str, Any],
    base: Path | None = None,
) -> Path:
    d = ensure_checkpoint_dir(base)
    p = d / LAST_RUN_FILE
    body = {
        **payload,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    p.write_text(json.dumps(body, ensure_ascii=False, indent=2), encoding="utf-8")
    return p


def load_last_run(base: Path | None = None) -> dict[str, Any]:
    p = last_run_path(base)
    if not p.is_file():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def filter_codes_resume(all_codes: list[str], base: Path | None = None) -> list[str]:
    """全量续传：跳过检查点里已成功的代码。"""
    ok_set = {SymbolNormalizer.normalize_cn_symbol(c) for c in load_ok_codes(base)}
    if not ok_set:
        return list(all_codes)
    return [c for c in all_codes if SymbolNormalizer.normalize_cn_symbol(c) not in ok_set]


def flush_sync_checkpoint(
    *,
    ok_batch: list[str] | None = None,
    failed: list[dict[str, Any]] | None = None,
    last_run: dict[str, Any] | None = None,
    base: Path | None = None,
) -> None:
    """增量落盘：续跑过程中周期性 append ok / 重写 failed，避免进程中断丢失进度。"""
    if ok_batch:
        append_ok_codes(ok_batch, base)
    if failed is not None:
        write_failed_codes(failed, base)
    if last_run is not None:
        save_last_run(last_run, base)
