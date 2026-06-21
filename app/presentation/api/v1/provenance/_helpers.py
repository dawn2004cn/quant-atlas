"""Provenance helper utilities."""

from __future__ import annotations


def health_color(health: float) -> str:
    """Map confidence to CSS color."""
    if health >= 0.85:
        return "green"
    if health >= 0.7:
        return "orange"
    return "red"
