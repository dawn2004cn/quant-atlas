"""Offline strategy tournament hard gates (SRS REQ-SRS-04)."""

from __future__ import annotations


def passes_tournament_gates(
    *,
    sharpe: float,
    max_drawdown: float,
    min_sharpe: float = 1.8,
    max_mdd: float = 0.12,
) -> bool:
    """Return True when Sharpe strictly exceeds floor and MDD is strictly below ceiling.

    SRS defaults: Sharpe > 1.8 and MDD < 12%.
    """
    return sharpe > min_sharpe and max_drawdown < max_mdd
