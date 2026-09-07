from __future__ import annotations

"""Hierarchical Risk Parity (Lopez de Prado / PyPortfolioOpt), numpy-only."""

from collections.abc import Sequence

import numpy as np


def hrp_weights(returns: dict[str, Sequence[float]]) -> dict[str, float]:
    """Allocate weights by hierarchical clustering + inverse-variance bisection."""
    tickers = [t for t, series in returns.items() if series]
    if not tickers:
        return {}
    if len(tickers) == 1:
        return {tickers[0]: 1.0}

    min_len = min(len(returns[t]) for t in tickers)
    if min_len < 2:
        even = 1.0 / len(tickers)
        return {t: even for t in tickers}

    matrix = np.array([list(returns[t])[:min_len] for t in tickers], dtype=float)
    cov = np.cov(matrix)
    if cov.ndim == 0:
        return {tickers[0]: 1.0}
    # Guard singular / zero-variance diagonals
    diag = np.diag(cov).copy()
    diag[diag <= 1e-12] = 1e-12
    cov = cov.copy()
    np.fill_diagonal(cov, diag)

    corr = np.corrcoef(matrix)
    corr = np.nan_to_num(corr, nan=0.0)
    np.fill_diagonal(corr, 1.0)
    dist = np.sqrt(np.clip((1.0 - corr) / 2.0, 0.0, 1.0))
    order = _single_linkage_order(dist)
    raw = _recursive_bisection(cov, order)
    return {tickers[i]: float(raw[i]) for i in range(len(tickers))}


def _single_linkage_order(dist: np.ndarray) -> list[int]:
    n = dist.shape[0]
    clusters: list[list[int]] = [[i] for i in range(n)]
    while len(clusters) > 1:
        best_d = float("inf")
        best_i = 0
        best_j = 1
        for i in range(len(clusters)):
            for j in range(i + 1, len(clusters)):
                d = min(dist[a, b] for a in clusters[i] for b in clusters[j])
                if d < best_d:
                    best_d = d
                    best_i, best_j = i, j
        merged = clusters[best_i] + clusters[best_j]
        clusters = [c for k, c in enumerate(clusters) if k not in (best_i, best_j)]
        clusters.append(merged)
    return clusters[0]


def _ivp(cov: np.ndarray) -> np.ndarray:
    iv = 1.0 / np.diag(cov)
    iv = np.where(np.isfinite(iv), iv, 0.0)
    total = float(iv.sum())
    if total <= 0:
        return np.ones(cov.shape[0]) / cov.shape[0]
    return iv / total


def _cluster_var(cov: np.ndarray, items: list[int]) -> float:
    sub = cov[np.ix_(items, items)]
    w = _ivp(sub)
    return float(w @ sub @ w)


def _recursive_bisection(cov: np.ndarray, order: list[int]) -> np.ndarray:
    weights = np.ones(cov.shape[0], dtype=float)
    clusters = [order]
    while clusters:
        nxt: list[list[int]] = []
        for cluster in clusters:
            if len(cluster) <= 1:
                continue
            mid = len(cluster) // 2
            left, right = cluster[:mid], cluster[mid:]
            if not left or not right:
                continue
            var_l = _cluster_var(cov, left)
            var_r = _cluster_var(cov, right)
            denom = var_l + var_r
            alpha = 1.0 - (var_l / denom) if denom > 1e-12 else 0.5
            weights[left] *= alpha
            weights[right] *= 1.0 - alpha
            nxt.extend([left, right])
        clusters = nxt
    total = float(weights.sum())
    return weights / total if total > 0 else np.ones_like(weights) / len(weights)
