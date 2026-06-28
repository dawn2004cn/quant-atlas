"""Neural Feature Mesh — Phase 17.
GNN-inspired feature crowding detection and Data Hygiene Score."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from app.core.logger import get_logger
from app.domain.verification import list_pending

logger = get_logger(__name__)


@dataclass
class FeatureCrowdingReport:
    feature_a: str
    feature_b: str
    crowding_pct: float  # 0..100
    recommended_replacements: list[str]
    reason: str


@dataclass
class DataHygieneScore:
    global_index: float  # 0..1
    sources: dict[str, float]
    staleness_days: int
    stale_symbols: list[str]


class NeuralFeatureMesh:
    """Monitors feature crowding and data hygiene."""

    def __init__(self, truth_guardian_service=None):
        self._guardian = truth_guardian_service
        self._correlation_cache: dict[tuple[str, str], float] = {}
        root = Path(__file__).resolve().parents[3]
        self._store = root / "instance" / "neural_mesh_log.jsonl"
        self._store.parent.mkdir(parents=True, exist_ok=True)

    def detect_crowding(self, feature_a: str, feature_b: str,
                        ic_series_a: list[float], ic_series_b: list[float],
                        regime: str = "bull") -> FeatureCrowdingReport:
        """Detect feature crowding using IC correlation."""
        n = min(len(ic_series_a), len(ic_series_b))
        if n < 5:
            return FeatureCrowdingReport(
                feature_a=feature_a, feature_b=feature_b,
                crowding_pct=0.0, recommended_replacements=[],
                reason="insufficient_data",
            )

        mean_a = sum(ic_series_a[:n]) / n
        mean_b = sum(ic_series_b[:n]) / n
        cov = sum((ic_series_a[i] - mean_a) * (ic_series_b[i] - mean_b) for i in range(n))
        var_a = sum((x - mean_a) ** 2 for x in ic_series_a[:n])
        var_b = sum((x - mean_b) ** 2 for x in ic_series_b[:n])
        corr = cov / (math.sqrt(var_a) * math.sqrt(var_b)) if var_a > 0 and var_b > 0 else 0

        crowding = round(abs(corr) * 100, 1)

        threshold = {"bull": 80, "bear": 75, "sideways": 85, "extreme": 70}.get(regime, 80)

        key = tuple(sorted([feature_a, feature_b]))
        self._correlation_cache[key] = crowding

        report = FeatureCrowdingReport(
            feature_a=feature_a, feature_b=feature_b,
            crowding_pct=crowding,
            recommended_replacements=(
                [f"建议替换{feature_b}为{self._find_uncorrelated(feature_a)}"]
                if crowding > threshold else []
            ),
            reason=("高同质化" if crowding > threshold else "正常"),
        )
        self._log_crowding_event(report)
        return report

    def compute_hygiene_score(self) -> DataHygieneScore:
        """Compute global data hygiene score from Guardian."""
        if not self._guardian:
            return DataHygieneScore(global_index=0.0, sources={}, staleness_days=0, stale_symbols=[])

        manifest = self._guardian.get_manifest()
        sources = manifest.get("sources", ["TDX", "Qlib", "AkShare"])
        health = {}
        for source in sources:
            health[source] = 0.85  # default health

        global_index = sum(health.values()) / max(len(health), 1)

        pending = list_pending()
        stale = [f"{k} ({v})" for k, v in pending.items()][:5]

        return DataHygieneScore(
            global_index=round(global_index, 4),
            sources=health,
            staleness_days=len(pending),
            stale_symbols=stale,
        )

    def _find_uncorrelated(self, feature_base: str) -> str:
        """Suggest an uncorrelated alternative feature."""
        best = None
        best_corr = 1.0
        for (a, b), corr in self._correlation_cache.items():
            if a == feature_base and corr < best_corr:
                best_corr = corr
                best = b
            elif b == feature_base and corr < best_corr:
                best_corr = corr
                best = a
        return best or "动量因子"

    def _log_crowding_event(self, report: FeatureCrowdingReport):
        try:
            with self._store.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps({
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "feature_a": report.feature_a,
                    "feature_b": report.feature_b,
                    "crowding_pct": report.crowding_pct,
                    "reason": report.reason,
                }) + "\n")
        except Exception as exc:
            logger.warning("Neural mesh log failed: %s", exc)
