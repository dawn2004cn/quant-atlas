"""Strategy code signing and signature storage.

The plugin loader refuses to execute arbitrary ``.py`` files unless they have
a recorded SHA-256 signature in ``instance/strategy_signatures.jsonl``.
This is a defense-in-depth measure: even if an attacker can write a file
into the strategy search path, the loader will not import it without an
administrator first signing it.
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class StrategySignatureService:
    """Records and verifies SHA-256 signatures for strategy plugin files."""

    def __init__(self, store_path: Path | None = None):
        if store_path is None:
            from app.config import INSTANCE_DIR

            store_path = Path(INSTANCE_DIR) / "strategy_signatures.jsonl"
        self._store_path = Path(store_path)
        self._store_path.parent.mkdir(parents=True, exist_ok=True)
        self._signatures: dict[str, dict[str, Any]] = {}
        self._load()

    def _load(self) -> None:
        if not self._store_path.is_file():
            return
        try:
            with self._store_path.open("r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        record = json.loads(line)
                        digest = record.get("sha256")
                        if digest:
                            self._signatures[digest] = record
                    except json.JSONDecodeError:
                        continue
        except OSError as exc:
            logger.warning("Failed to load strategy signatures: %s", exc)

    def _persist(self, record: dict[str, Any]) -> None:
        try:
            with self._store_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
        except OSError as exc:
            logger.error("Failed to persist strategy signature: %s", exc)

    @staticmethod
    def compute_digest(file_path: Path | str) -> str:
        """Compute the SHA-256 digest of a file's contents."""
        h = hashlib.sha256()
        with Path(file_path).open("rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        return h.hexdigest()

    def is_signed(self, file_path: Path | str) -> bool:
        """Return True if the file has a valid recorded signature."""
        digest = self.compute_digest(file_path)
        return digest in self._signatures

    def sign_file(
        self,
        file_path: Path | str,
        admin_user_id: str | int,
        *,
        overwrite: bool = False,
    ) -> str:
        """Record a signature for *file_path* and return the digest."""
        digest = self.compute_digest(file_path)
        if digest in self._signatures and not overwrite:
            return digest

        record = {
            "sha256": digest,
            "path": str(Path(file_path).resolve()),
            "signed_at": time.time(),
            "signed_by": str(admin_user_id),
        }
        self._signatures[digest] = record
        self._persist(record)
        logger.info("Signed strategy file %s with digest %s", file_path, digest)
        return digest

    def get_signature_info(self, file_path: Path | str) -> dict[str, Any] | None:
        digest = self.compute_digest(file_path)
        return self._signatures.get(digest)
