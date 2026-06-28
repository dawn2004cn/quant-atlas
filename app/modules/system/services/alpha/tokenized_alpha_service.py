from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from app.domain.alpha.factor_manager import FactorMetrics


@dataclass
class AlphaTokenManifest:
    token_id: str
    factor_id: str
    owner_id: int
    token_name: str
    token_symbol: str
    description: str = ""
    ic_history: list[float] = field(default_factory=list)
    live_performance: dict[str, float] = field(default_factory=dict)
    visibility: str = "public"
    access_requirements: dict[str, Any] = field(default_factory=dict)
    contract_address: str | None = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "token_id": self.token_id,
            "factor_id": self.factor_id,
            "owner_id": self.owner_id,
            "token_name": self.token_name,
            "token_symbol": self.token_symbol,
            "description": self.description,
            "ic_history": self.ic_history,
            "live_performance": self.live_performance,
            "visibility": self.visibility,
            "access_requirements": self.access_requirements,
            "contract_address": self.contract_address,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AlphaTokenManifest:
        return cls(**data)


@dataclass
class ReputationShardRecord:
    user_id: int
    shard_id: str
    reputation_score: float
    contribution_count: int = 0
    live_days: int = 0
    last_live_at: str = ""
    locked: bool = False
    created_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return self.__dict__.copy()

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ReputationShardRecord:
        return cls(**data)


class TokenizedAlphaService:
    def __init__(self, store_path: str | Path | None = None):
        root = Path(__file__).resolve().parents[4]
        self._store_path = Path(store_path) if store_path else root / "instance" / "alpha_tokens.jsonl"
        self._store_path.parent.mkdir(parents=True, exist_ok=True)
        self._reputation_store = root / "instance" / "reputation_shards.jsonl"
        self._cache: dict[str, AlphaTokenManifest] = {}

    def tokenize_factor(self, factor_id: str, owner_id: int, performance_summary: dict, metadata: dict | None = None) -> AlphaTokenManifest:
        metadata = metadata or {}
        perf = FactorMetrics(**performance_summary) if performance_summary else FactorMetrics(factor_name=factor_id)
        token_id = "tk." + uuid4().hex[:16]
        manifest = AlphaTokenManifest(
            token_id=token_id,
            factor_id=factor_id,
            owner_id=owner_id,
            token_name=metadata.get("token_name", f"Factor {factor_id[:8]}"),
            token_symbol="A" + token_id[-6:].upper(),
            description=metadata.get("description", ""),
            ic_history=list(getattr(perf, "historical_ics", None) or getattr(perf, "ic_history", []) or []),
            live_performance={
                "ic_mean": round(perf.ic_mean, 4),
                "ic_std": round(perf.ic_std, 4),
                "ir": round(perf.ir, 4),
                "turnover": round(perf.turnover, 4),
            },
            visibility=metadata.get("visibility", "public"),
            access_requirements=metadata.get("access_requirements", {}),
            contract_address=metadata.get("contract_address"),
        )
        self._save_manifest(manifest)
        self._update_reputation_shard(owner_id, token_id, perf.ic_mean > 0)
        return manifest

    def get_manifest(self, token_id: str) -> AlphaTokenManifest | None:
        if token_id in self._cache:
            return self._cache[token_id]
        if not self._store_path.exists():
            return None
        with self._store_path.open("r", encoding="utf-8") as fh:
            for line in fh:
                if not line.strip():
                    continue
                data = json.loads(line)
                if data.get("token_id") == token_id:
                    manifest = AlphaTokenManifest.from_dict(data)
                    self._cache[token_id] = manifest
                    return manifest
        return None

    def list_manifests(self) -> list[dict[str, Any]]:
        rows = []
        if not self._store_path.exists():
            return rows
        with self._store_path.open("r", encoding="utf-8") as fh:
            for line in fh:
                if line.strip():
                    rows.append(json.loads(line))
        return rows

    def _save_manifest(self, manifest: AlphaTokenManifest) -> None:
        with self._store_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(manifest.to_dict(), ensure_ascii=False) + "\n")
        self._cache[manifest.token_id] = manifest

    def _update_reputation_shard(self, user_id: int, token_id: str, success: bool) -> None:
        rec = self._get_reputation_record(user_id) or ReputationShardRecord(
            user_id=user_id,
            shard_id=f"rs.{user_id:x}",
            reputation_score=0.0,
        )
        rec.reputation_score = min(100.0, max(0.0, rec.reputation_score + (1.0 if success else -0.5)))
        rec.contribution_count += 1
        rec.live_days += 1 if success else 0
        rec.last_live_at = datetime.now(timezone.utc).isoformat()
        with self._reputation_store.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec.to_dict(), ensure_ascii=False) + "\n")

    def _get_reputation_record(self, user_id: int) -> ReputationShardRecord | None:
        if not self._reputation_store.exists():
            return None
        with self._reputation_store.open("r", encoding="utf-8") as fh:
            for line in fh:
                if not line.strip():
                    continue
                data = json.loads(line)
                if int(data.get("user_id", -1)) == user_id:
                    return ReputationShardRecord.from_dict(data)
        return None

    def get_hero_board(self, limit: int = 10) -> list[dict[str, Any]]:
        rows = []
        if not self._reputation_store.exists():
            return rows
        with self._reputation_store.open("r", encoding="utf-8") as fh:
            for line in fh:
                if line.strip():
                    rows.append(ReputationShardRecord.from_dict(json.loads(line)))
        rows.sort(key=lambda item: item.reputation_score, reverse=True)
        return [
            {
                "user_id": rec.user_id,
                "reputation_score": round(rec.reputation_score, 2),
                "contribution_count": rec.contribution_count,
                "live_days": rec.live_days,
            }
            for rec in rows[:limit]
        ]


__all__ = ["TokenizedAlphaService", "AlphaTokenManifest", "ReputationShardRecord"]
