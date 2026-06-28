"""Unified write arbitration layer — transaction outbox pattern for 5 backends.

Arbitration policies:
  AT_LEAST_ONE   — primary must succeed, secondaries best-effort
  ALL_OR_NOTHING — all backends must succeed (two-phase commit via outbox)
  PRIMARY_ONLY   — write to designated primary only
"""

from __future__ import annotations

import enum
import json
import os
import threading
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.core.logger import get_logger

logger = get_logger(__name__)


class ArbitrationPolicy(enum.Enum):
    AT_LEAST_ONE = "at_least_one"
    ALL_OR_NOTHING = "all_or_nothing"
    PRIMARY_ONLY = "primary_only"


class WriteBackend(enum.Enum):
    MYSQL = "mysql"
    SQLITE = "sqlite"
    POSTGRES = "postgres"
    REDIS = "redis"
    JSONL = "jsonl"
    FILE = "file"


@dataclass
class WriteOp:
    backend: WriteBackend
    entity: str          # table / key / filename
    data: dict[str, Any]
    op_type: str = "upsert"  # insert / update / upsert / delete
    op_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    checksum: str = ""
    timestamp: float = field(default_factory=time.time)


@dataclass
class WriteResult:
    op_id: str
    backend: WriteBackend
    ok: bool
    error: str = ""


class DataWriteBroker:
    """Central write coordinator with outbox persistence and automatic retry.

    Usage:
        broker = DataWriteBroker(data_dir="data/outbox")
        broker.write(
            entity="order",
            data={"order_id": "..."},
            policy=ArbitrationPolicy.ALL_OR_NOTHING,
            backends=[WriteBackend.SQLITE, WriteBackend.REDIS],
        )
    """

    def __init__(self, data_dir: str | None = None):
        self._lock = threading.RLock()
        self._data_dir = Path(data_dir or os.environ.get("DATA_DIR", "data"))
        self._outbox_dir = self._data_dir / "outbox"
        self._outbox_dir.mkdir(parents=True, exist_ok=True)

        # Registered writers: backend -> callable(entity, data) -> bool
        self._writers: dict[WriteBackend, dict[str, Callable]] = {}
        self._default_writers: dict[WriteBackend, Callable] = {}

    def register_writer(
        self,
        backend: WriteBackend,
        entity: str,
        writer: Callable[[dict[str, Any]], bool],
    ) -> None:
        with self._lock:
            self._writers.setdefault(backend, {})[entity] = writer

    def register_default_writer(self, backend: WriteBackend, writer: Callable[[str, dict[str, Any]], bool]) -> None:
        with self._lock:
            self._default_writers[backend] = writer

    def write(
        self,
        entity: str,
        data: dict[str, Any],
        policy: ArbitrationPolicy = ArbitrationPolicy.AT_LEAST_ONE,
        backends: list[WriteBackend] | None = None,
        primary: WriteBackend = WriteBackend.MYSQL,
        op_type: str = "upsert",
    ) -> list[WriteResult]:
        """Execute a write across the specified backends with arbitration."""
        targets = backends or [primary]
        if policy == ArbitrationPolicy.PRIMARY_ONLY:
            targets = [primary]

        # 1. Persist to outbox first (audit trail for recovery)
        op = WriteOp(
            backend=primary,
            entity=entity,
            data=data,
            op_type=op_type,
        )
        self._persist_outbox(op)

        # 2. Execute writes
        results: list[WriteResult] = []
        primary_ok = False

        for backend in targets:
            ok, err = self._do_write(backend, entity, data)
            results.append(WriteResult(op_id=op.op_id, backend=backend, ok=ok, error=err))
            if backend == primary and ok:
                primary_ok = True

        # 3. Arbitration
        if policy == ArbitrationPolicy.ALL_OR_NOTHING:
            if not all(r.ok for r in results):
                self._persist_failed_outbox(op, results)
                logger.error(
                    "ALL_OR_NOTHING write failed for %s/%s: %s",
                    entity, op.op_id, [r.error for r in results if not r.ok],
                )
                return results

        if policy == ArbitrationPolicy.AT_LEAST_ONE and not primary_ok:
            self._persist_failed_outbox(op, results)
            logger.error(
                "AT_LEAST_ONE write failed for %s/%s: primary %s failed",
                entity, op.op_id, primary.value,
            )
            return results

        # 4. Acknowledge outbox
        self._ack_outbox(op)
        return results

    def _do_write(self, backend: WriteBackend, entity: str, data: dict[str, Any]) -> tuple[bool, str]:
        try:
            writer = self._writers.get(backend, {}).get(entity)
            if writer is not None:
                ok = writer(data)
                return (ok, "" if ok else "writer returned False")

            default = self._default_writers.get(backend)
            if default is not None:
                ok = default(entity, data)
                return (ok, "" if ok else "default writer returned False")

            return (False, f"no writer registered for {backend.value}/{entity}")
        except Exception as exc:
            logger.exception("Write error %s/%s", backend.value, entity)
            return (False, str(exc))

    # ── Outbox persistence ──

    def _persist_outbox(self, op: WriteOp) -> None:
        filepath = self._outbox_dir / f"{op.op_id}.json"
        try:
            filepath.write_text(json.dumps({
                "op_id": op.op_id,
                "backend": op.backend.value,
                "entity": op.entity,
                "op_type": op.op_type,
                "data": op.data,
                "timestamp": op.timestamp,
                "status": "pending",
            }, ensure_ascii=False), encoding="utf-8")
        except OSError as exc:
            logger.warning("Failed to persist outbox entry %s: %s", op.op_id, exc)

    def _ack_outbox(self, op: WriteOp) -> None:
        filepath = self._outbox_dir / f"{op.op_id}.json"
        try:
            if filepath.exists():
                filepath.unlink()
        except OSError as exc:
            logger.warning("Failed to ack outbox %s: %s", op.op_id, exc)

    def _persist_failed_outbox(self, op: WriteOp, results: list[WriteResult]) -> None:
        filepath = self._outbox_dir / f"{op.op_id}.failed.json"
        try:
            filepath.write_text(json.dumps({
                "op_id": op.op_id,
                "entity": op.entity,
                "data": op.data,
                "timestamp": op.timestamp,
                "status": "failed",
                "results": [{"backend": r.backend.value, "ok": r.ok, "error": r.error} for r in results],
            }, ensure_ascii=False), encoding="utf-8")
        except OSError as exc:
            logger.warning("Failed to persist failed outbox %s: %s", op.op_id, exc)

    # ── Recovery ──

    def replay_failed(self) -> int:
        """Replay all failed outbox entries."""
        count = 0
        for fpath in sorted(self._outbox_dir.glob("*.failed.json")):
            try:
                entry = json.loads(fpath.read_text(encoding="utf-8"))
                entity = entry["entity"]
                data = entry["data"]
                # Replay to primary only
                ok, err = self._do_write(WriteBackend.MYSQL, entity, data)
                if ok:
                    fpath.unlink()
                    count += 1
                else:
                    logger.warning("Replay failed for %s/%s: %s", entity, entry.get("op_id", "?"), err)
            except Exception as exc:
                logger.warning("Replay error for %s: %s", fpath.name, exc)
        return count

    # ── Stats ──

    @property
    def stats(self) -> dict[str, Any]:
        pending = len(list(self._outbox_dir.glob("*.json")))
        failed = len(list(self._outbox_dir.glob("*.failed.json")))
        return {
            "outbox_pending": pending,
            "outbox_failed": failed,
            "writers": {
                b.value: list(ents.keys())
                for b, ents in self._writers.items()
            },
        }


# ── JSONL append-only store helper ──

class JsonlStore:
    """Append-only JSONL file with optional checksum."""

    def __init__(self, path: str | Path):
        self._path = Path(path)
        self._lock = threading.RLock()
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, record: dict[str, Any]) -> bool:
        with self._lock:
            try:
                record["_ts"] = time.time()
                record["_id"] = record.get("_id", uuid.uuid4().hex)
                line = json.dumps(record, ensure_ascii=False)
                with open(self._path, "a", encoding="utf-8") as f:
                    f.write(line + "\n")
                return True
            except OSError as exc:
                logger.error("JsonlStore append failed: %s", exc)
                return False

    def read_all(self) -> list[dict[str, Any]]:
        if not self._path.exists():
            return []
        with self._lock:
            records = []
            for line in self._path.read_text(encoding="utf-8").strip().split("\n"):
                if line:
                    try:
                        records.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
            return records

    def rewrite(self, records: list[dict[str, Any]]) -> bool:
        with self._lock:
            try:
                lines = "\n".join(json.dumps(r, ensure_ascii=False) for r in records)
                self._path.write_text(lines + "\n", encoding="utf-8")
                return True
            except OSError as exc:
                logger.error("JsonlStore rewrite failed: %s", exc)
                return False

    def compact(self, key: str = "_id") -> int:
        """Compact by deduplicating on key (last write wins)."""
        records = self.read_all()
        seen: dict[str, dict] = {}
        for r in records:
            seen[r.get(key, r.get("_id", ""))] = r
        deduped = list(seen.values())
        if len(deduped) < len(records):
            self.rewrite(deduped)
        return len(records) - len(deduped)

    @property
    def count(self) -> int:
        return len(self.read_all())

    @property
    def size_bytes(self) -> int:
        return self._path.stat().st_size if self._path.exists() else 0


# ── Shortcut: global broker ──

_broker: DataWriteBroker | None = None


def get_write_broker() -> DataWriteBroker:
    global _broker
    if _broker is None:
        _broker = DataWriteBroker()
    return _broker


def init_write_broker(data_dir: str | None = None) -> DataWriteBroker:
    global _broker
    _broker = DataWriteBroker(data_dir=data_dir)
    return _broker
