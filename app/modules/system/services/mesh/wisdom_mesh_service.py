"""Wisdom Mesh — de-identified strategy sharing and crowdfactor voting."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.core.logger import get_logger
from app.domain.mesh.wisdom_mesh_schema import (
    CrowdfactorContribution,
    DeIdentifiedStrategy,
)

logger = get_logger(__name__)


class WisdomMeshService:
    """JSONL-backed store for anonymized strategies and factor votes."""

    def __init__(self, store_path: str | Path | None = None) -> None:
        root = Path(__file__).resolve().parents[4]
        self._store_path = Path(store_path) if store_path else root / "instance" / "wisdom_mesh.jsonl"
        self._store_path.parent.mkdir(parents=True, exist_ok=True)
        self._strategies: dict[str, DeIdentifiedStrategy] = {}
        self._contributions: dict[str, CrowdfactorContribution] = {}
        self._participant_scores: dict[str, int] = {}
        self._load()

    def list_shared_strategies(
        self,
        *,
        limit: int = 20,
        filter_by: str = "top",
    ) -> list[dict[str, Any]]:
        items = list(self._strategies.values())
        if filter_by == "recent":
            items.sort(key=lambda s: s.contributed_at, reverse=True)
        else:
            items.sort(key=lambda s: s.success_score, reverse=True)
        return [s.to_dict() for s in items[: max(1, limit)]]

    def upload_deidentified_strategy(
        self,
        *,
        user_id: str,
        strategy_spec: dict[str, Any],
        performance_summary: dict[str, Any] | None = None,
    ) -> DeIdentifiedStrategy:
        _ = user_id  # stripped — mesh stores no personal identifiers
        perf = performance_summary or {}
        success = float(perf.get("sharpe") or perf.get("total_return") or 0.0)
        strategy = DeIdentifiedStrategy(
            strategy_name=str(strategy_spec.get("name") or strategy_spec.get("strategy_name") or "shared_strategy"),
            strategy_spec=strategy_spec,
            performance_summary=perf,
            success_score=success,
            contributed_at=datetime.now(timezone.utc).isoformat(),
        )
        self._strategies[strategy.id] = strategy
        self._append({"type": "strategy", "data": strategy.to_dict()})
        logger.info("WisdomMesh upload strategy_id=%s", strategy.id)
        return strategy

    def get_shared_strategy(self, strategy_id: str) -> dict[str, Any] | None:
        strategy = self._strategies.get(str(strategy_id))
        return strategy.to_dict() if strategy else None

    def vote_on_factor(
        self,
        *,
        voter_id: str,
        strategy_id: str,
        factor_name: str,
        proposed_weight: float,
        rationale: str = "",
    ) -> CrowdfactorContribution:
        if strategy_id not in self._strategies:
            raise ValueError("strategy_not_found")
        key = f"{strategy_id}:{factor_name}:{proposed_weight}"
        contribution = self._contributions.get(key)
        if contribution is None:
            contribution = CrowdfactorContribution(
                strategy_id=strategy_id,
                factor_name=factor_name,
                proposed_weight=proposed_weight,
                rationale=rationale,
                created_at=datetime.now(timezone.utc).isoformat(),
            )
            self._contributions[key] = contribution
        contribution.votes_for += 1
        strategy = self._strategies[strategy_id]
        strategy.vote_count += 1
        strategy.vote_for += 1
        self._participant_scores[voter_id] = self._participant_scores.get(voter_id, 0) + 1
        self._append({"type": "vote", "data": contribution.to_dict(), "voter": voter_id})
        return contribution

    def get_leaderboard(self, *, period: str = "weekly") -> list[dict[str, Any]]:
        _ = period
        ranked = sorted(self._participant_scores.items(), key=lambda kv: kv[1], reverse=True)
        return [
            {"anonymized_id": f"user_{idx:04d}", "score": score, "rank": idx + 1}
            for idx, (_uid, score) in enumerate(ranked[:50])
        ]

    def _load(self) -> None:
        if not self._store_path.exists():
            return
        try:
            with self._store_path.open("r", encoding="utf-8") as fh:
                for line in fh:
                    if not line.strip():
                        continue
                    row = json.loads(line)
                    kind = row.get("type")
                    data = row.get("data") or {}
                    if kind == "strategy":
                        strategy = DeIdentifiedStrategy.from_dict(data)
                        self._strategies[strategy.id] = strategy
                    elif kind == "vote":
                        contrib = CrowdfactorContribution(
                            id=data.get("id", ""),
                            strategy_id=data.get("strategy_id", ""),
                            factor_name=data.get("factor_name", ""),
                            original_weight=float(data.get("original_weight", 0)),
                            proposed_weight=float(data.get("proposed_weight", 0)),
                            votes_for=int(data.get("votes_for", 0)),
                            votes_against=int(data.get("votes_against", 0)),
                            rationale=data.get("rationale", ""),
                            created_at=data.get("created_at", ""),
                        )
                        key = f"{contrib.strategy_id}:{contrib.factor_name}:{contrib.proposed_weight}"
                        self._contributions[key] = contrib
                        voter = row.get("voter")
                        if voter:
                            self._participant_scores[str(voter)] = (
                                self._participant_scores.get(str(voter), 0) + 1
                            )
        except Exception:
            logger.warning("WisdomMesh store load failed", exc_info=True)

    def _append(self, row: dict[str, Any]) -> None:
        with self._store_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")


__all__ = ["WisdomMeshService"]
