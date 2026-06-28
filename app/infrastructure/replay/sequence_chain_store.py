from __future__ import annotations

"""JSONL persistence for SequenceChain provenance records."""

import json
from pathlib import Path
from typing import Any

from app.core.logger import get_logger
from app.domain.sequence_chain import SequenceChain

logger = get_logger(__name__)


class SequenceChainStore:
    """Append-only store for provenance chains."""

    def __init__(self, base_dir: Path | str) -> None:
        self._base = Path(base_dir)
        self._base.mkdir(parents=True, exist_ok=True)
        self._index_path = self._base / "chains_index.jsonl"

    def append(self, chain: SequenceChain) -> None:
        line = json.dumps(chain.model_dump(), ensure_ascii=False)
        with self._index_path.open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")

    def load_recent(
        self,
        *,
        symbol: str | None = None,
        team_id: int | None = None,
        visibility: str | None = None,
        limit: int = 50,
    ) -> list[SequenceChain]:
        if not self._index_path.exists():
            return []
        rows: list[SequenceChain] = []
        sym_key = (symbol or "").strip().lower()
        try:
            with self._index_path.open("r", encoding="utf-8") as fh:
                for raw in fh:
                    raw = raw.strip()
                    if not raw:
                        continue
                    try:
                        data: dict[str, Any] = json.loads(raw)
                    except json.JSONDecodeError:
                        continue
                    if sym_key and str(data.get("symbol", "")).lower() != sym_key:
                        continue
                    if team_id is not None:
                        row_team = data.get("team_id")
                        row_vis = str(data.get("visibility") or "private")
                        if row_team != team_id and row_vis != "public":
                            continue
                    if visibility and str(data.get("visibility") or "private") != visibility:
                        continue
                    rows.append(SequenceChain.model_validate(data))
        except OSError as exc:
            logger.warning("sequence_chain_store load_recent: %s", exc)
        rows.sort(key=lambda c: c.updated_at, reverse=True)
        return rows[: max(1, limit)]

    def load_by_id(self, provenance_id: str) -> SequenceChain | None:
        if not self._index_path.exists():
            return None
        try:
            with self._index_path.open("r", encoding="utf-8") as fh:
                for raw in fh:
                    raw = raw.strip()
                    if not raw or provenance_id not in raw:
                        continue
                    data = json.loads(raw)
                    if data.get("provenance_id") == provenance_id:
                        return SequenceChain.model_validate(data)
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("sequence_chain_store load_by_id: %s", exc)
        return None
