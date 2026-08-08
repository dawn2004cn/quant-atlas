"""Temporal Knowledge Graph — Phase 18 Apex Quantum.

Compresses OHLCV price/volume sequences into fixed-length vectors,
stores them with timestamps, and enables historical similarity
matching ("historical resonance") for retail investors.

Usage:
    kernel = TemporalKGCores()
    # Register historical episodes
    kernel.register_episode("2024-03-01", "600519", bars, metadata={})
    # Query: what does 600519 look like now?
    results = kernel.resonance("600519", current_bars, top_k=3)
"""

from __future__ import annotations

import hashlib
import json
import math
import struct
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.core.logger import get_logger

logger = get_logger(__name__)


# ── Data structures ───────────────────────────────────────────────

@dataclass
class TimeSeriesVector:
    """Fixed-length feature vector extracted from OHLCV bars."""
    dims: list[float]  # 32-d normalized vector
    source_symbol: str
    window_start: str  # ISO timestamp
    window_end: str

    def to_dict(self) -> dict:
        return {
            "dims": self.dims,
            "source_symbol": self.source_symbol,
            "window_start": self.window_start,
            "window_end": self.window_end,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "TimeSeriesVector":
        return cls(
            dims=d["dims"],
            source_symbol=d["source_symbol"],
            window_start=d["window_start"],
            window_end=d["window_end"],
        )


@dataclass
class HistoricalEpisode:
    """A historical episode: bars + context + outcome."""
    episode_id: str
    symbol: str
    window_start: str
    window_end: str
    context: dict[str, Any]  # e.g. volume_spike, limit_up, gap_down
    outcome: dict[str, Any]  # e.g. next_5d_return, max_gain_pct
    vector: TimeSeriesVector
    evidence: list[str] = field(default_factory=list)  # supporting evidence notes


@dataclass
class ResonanceResult:
    """One resonance match result."""
    episode_id: str
    symbol: str
    window_start: str
    context: dict[str, Any]
    similarity: float  # 0..1
    outcome_summary: str  # human-readable outcome
    confidence_pct: float  # 0..100 based on evidence count


# ── Feature extraction ───────────────────────────────────────────

class FeatureExtractor:
    """Extracts a 32-d vector from OHLCV bars.

    The vector captures: trend, volatility, volume pattern, momentum,
    mean-reversion signals, and intraday shape distribution.

    Design: 32 dims = 4 windows × 8 features per window.
    Each feature is z-scored within the window for robustness.
    """

    DIMS = 32
    WINDOW_DIMS = 4

    @staticmethod
    def _safe_mean(xs: list[float]) -> float:
        return sum(xs) / max(len(xs), 1)

    @staticmethod
    def _safe_std(xs: list[float]) -> float:
        if len(xs) < 2:
            return 1.0
        m = FeatureExtractor._safe_mean(xs)
        var = sum((x - m) ** 2 for x in xs) / (len(xs) - 1)
        return max(math.sqrt(var), 1e-9)

    @staticmethod
    def _zscore(xs: list[float]) -> list[float]:
        m = FeatureExtractor._safe_mean(xs)
        s = FeatureExtractor._safe_std(xs)
        return [(x - m) / s for x in xs]

    @staticmethod
    def _normalize(xs: list[float]) -> list[float]:
        """L2-normalize."""
        norm = math.sqrt(sum(x * x for x in xs)) or 1.0
        return [x / norm for x in xs]

    @classmethod
    def extract(cls, bars: list[dict[str, Any]]) -> TimeSeriesVector:
        """Extract a fixed-length vector from N OHLCV bars.

        Expects bars sorted ascending by date, each dict with keys:
        date, open, high, low, close, volume.

        Returns a 32-d vector. If fewer than 5 bars, returns zeros.
        """
        n = len(bars)
        if n < 1:
            return TimeSeriesVector(
                dims=[0.0] * cls.DIMS,
                source_symbol="",
                window_start="",
                window_end="",
            )

        closes = [float(b.get("close", 0)) for b in bars]
        volumes = [float(b.get("volume", 0)) for b in bars]
        highs = [float(b.get("high", 0)) for b in bars]
        lows = [float(b.get("low", 0)) for b in bars]
        dates = [b.get("date", "") for b in bars]

        # Compute features for each of 4 windows
        # If bars < 4, use single window over all data
        window_size = max(n // cls.WINDOW_DIMS, 1)
        all_features = []

        for w in range(cls.WINDOW_DIMS):
            start = w * window_size
            end = min(start + window_size, n)
            if start >= n:
                all_features.extend([0.0] * 8)
                continue

            wc = closes[start:end]
            wv = volumes[start:end]
            wh = highs[start:end]
            wl = lows[start:end]

            # Feature 1: close trend (slope via linear regression)
            if len(wc) > 1:
                mean_x = (len(wc) - 1) / 2.0
                slope = sum(i * (wc[i] / wc[0] - 1) for i in range(len(wc))) / max(len(wc), 1)
                trend = slope / max(abs(slope), 1e-9)
            else:
                trend = 0.0

            # Feature 2: volatility (normalized std)
            volatility = FeatureExtractor._safe_std(wc) / max(FeatureExtractor._safe_mean(wc), 1e-9)

            # Feature 3: volume spike (ratio of mean to global)
            vol_mean = FeatureExtractor._safe_mean(wv)
            vol_std = FeatureExtractor._safe_std(wv)
            volume_burst = vol_mean / max(vol_std, 1e-9)

            # Feature 4: high-low range (intraday intensity)
            ranges = [(wh[i] - wl[i]) / max(wl[i], 1e-9) for i in range(len(wl))]
            avg_range = FeatureExtractor._safe_mean(ranges)

            # Feature 5: mean reversion signal (close relative to range)
            mr = (wc[-1] - FeatureExtractor._safe_mean(wc)) / max(FeatureExtractor._safe_std(wc), 1e-9)

            # Feature 6: momentum (last close vs mean)
            momentum = (wc[-1] - FeatureExtractor._safe_mean(wc)) / max(FeatureExtractor._safe_mean(wc), 1e-9)

            # Feature 7: volume trend (z-scored last quarter)
            half = len(wv) // 2
            if half > 0 and len(wv) > 1:
                vol_trend = (FeatureExtractor._safe_mean(wv[half:]) - FeatureExtractor._safe_mean(wv[:half])) / max(FeatureExtractor._safe_std(wv), 1e-9)
            else:
                vol_trend = 0.0

            # Feature 8: price position (where last close falls in range)
            w_max = max(wh) if wh else 1.0
            w_min = min(wl) if wl else 0.0
            price_pos = (wc[-1] - w_min) / max(w_max - w_min, 1e-9) if w_max > w_min else 0.5

            features = [trend, volatility, volume_burst, avg_range, mr, momentum, vol_trend, price_pos]
            all_features.extend(features)

        # L2-normalize the 32-d vector
        normalized = FeatureExtractor._normalize(all_features)
        return TimeSeriesVector(
            dims=normalized,
            source_symbol=bars[-1].get("code", bars[-1].get("symbol", "")),
            window_start=dates[0] if dates else "",
            window_end=dates[-1] if dates else "",
        )


# ── Resonance engine ─────────────────────────────────────────────

class TemporalKGCores:
    """Temporal Knowledge Graph engine for historical pattern matching.

    Stores compressed OHLCV vectors with metadata, enables similarity
    search via cosine distance.
    """

    def __init__(self, store_path: str | Path | None = None):
        self._episodes: dict[str, HistoricalEpisode] = {}
        self._index: dict[str, list[str]] = {}  # symbol -> [episode_ids]
        self._lock = None  # threading.Lock()  # In-process only for prototype
        self._store_path = Path(store_path) if store_path else Path(__file__).resolve().parents[3] / "instance" / "temporal_kg" / "episodes.jsonl"
        self._store_path.parent.mkdir(parents=True, exist_ok=True)
        self._load()

    def register_episode(self, episode: HistoricalEpisode) -> str:
        """Register a historical episode."""
        self._episodes[episode.episode_id] = episode
        sym = episode.symbol
        if sym not in self._index:
            self._index[sym] = []
        self._index[sym].append(episode.episode_id)
        self._persist_episode(episode)
        return episode.episode_id

    def register_episode_batch(self, episodes: list[HistoricalEpisode]) -> int:
        """Register multiple episodes at once."""
        count = 0
        for ep in episodes:
            self.register_episode(ep)
            count += 1
        return count

    def resonance(
        self,
        symbol: str,
        current_bars: list[dict[str, Any]],
        *,
        top_k: int = 5,
        min_similarity: float = 0.6,
    ) -> list[ResonanceResult]:
        """Find historical episodes most similar to current bars.

        Returns ResonanceResult sorted by similarity descending.
        """
        current_vector = FeatureExtractor.extract(current_bars)
        query_dims = current_vector.dims

        # Search episodes for this symbol (or cross-symbol if no match)
        candidates = self._index.get(symbol, [])
        if not candidates:
            # Cross-symbol search: search all
            candidates = [eid for eps in self._index.values() for eid in eps]

        results = []
        for eid in candidates:
            episode = self._episodes.get(eid)
            if not episode:
                continue

            sim = _cosine(query_dims, episode.vector.dims)
            if sim < min_similarity:
                continue

            # Build outcome summary
            outcome = episode.outcome
            outcome_summary = ""
            if outcome:
                ret = outcome.get("next_5d_return")
                if ret is not None:
                    outcome_summary = f"5日涨幅: {ret:+.1%}"
                else:
                    outcome_summary = ", ".join(f"{k}: {v}" for k, v in outcome.items() if k != "next_5d_return")

            results.append(ResonanceResult(
                episode_id=episode.episode_id,
                symbol=episode.symbol,
                window_start=episode.window_start,
                context=episode.context,
                similarity=round(sim, 4),
                outcome_summary=outcome_summary,
                confidence_pct=min(95, 60 + len(episode.evidence) * 5),
            ))

        results.sort(key=lambda r: r.similarity, reverse=True)
        return results[:top_k]

    def query_by_symbol(self, symbol: str) -> list[dict[str, Any]]:
        """List all episodes for a symbol."""
        eps = self._episodes.get(symbol)
        if not eps:
            return []
        return [
            {
                "episode_id": ep.episode_id,
                "symbol": ep.symbol,
                "window_start": ep.window_start,
                "window_end": ep.window_end,
                "context": ep.context,
                "outcome": ep.outcome,
            }
            for eid in self._index.get(symbol, [])
            if (ep := self._episodes.get(eid))
        ]

    def stats(self) -> dict[str, Any]:
        return {
            "total_episodes": len(self._episodes),
            "symbols_covered": len(self._index),
        }

    # ── Persistence ───────────────────────────────────────────────

    def _persist_episode(self, episode: HistoricalEpisode) -> None:
        try:
            with self._store_path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps({
                    "episode_id": episode.episode_id,
                    "symbol": episode.symbol,
                    "window_start": episode.window_start,
                    "window_end": episode.window_end,
                    "context": episode.context,
                    "outcome": episode.outcome,
                    "evidence": episode.evidence,
                    "vector": episode.vector.to_dict(),
                }, ensure_ascii=False) + "\n")
        except Exception as exc:
            logger.warning("TemporalKG persist failed: %s", exc)

    def _load(self) -> None:
        """Load episodes from JSONL store."""
        if not self._store_path.exists():
            return
        try:
            with self._store_path.open("r", encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        d = json.loads(line)
                        vector = TimeSeriesVector.from_dict(d["vector"])
                        episode = HistoricalEpisode(
                            episode_id=d["episode_id"],
                            symbol=d["symbol"],
                            window_start=d["window_start"],
                            window_end=d["window_end"],
                            context=d.get("context", {}),
                            outcome=d.get("outcome", {}),
                            vector=vector,
                            evidence=d.get("evidence", []),
                        )
                        self._episodes[episode.episode_id] = episode
                        sym = episode.symbol
                        if sym not in self._index:
                            self._index[sym] = []
                        self._index[sym].append(episode.episode_id)
                    except Exception as exc:
                        logger.warning("TemporalKG load error: %s", exc)
        except Exception as exc:
            logger.warning("TemporalKG load failed: %s", exc)


# ── Utility ───────────────────────────────────────────────────────

def _cosine(a: list[float], b: list[float]) -> float:
    if len(a) != len(b) or not a:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def _make_episode_id(symbol: str, start: str, end: str, seed: str = "0") -> str:
    key = f"{symbol}:{start}:{end}:{seed}"
    return hashlib.sha256(key.encode()).hexdigest()[:16]


def get_temporal_kg() -> TemporalKGCores:
    """Get or create the global TemporalKG singleton."""
    # Module-level singleton
    import __main__ as main_mod
    if not hasattr(main_mod, "_temporal_kg_instance"):
        main_mod._temporal_kg_instance = TemporalKGCores()
    return main_mod._temporal_kg_instance
