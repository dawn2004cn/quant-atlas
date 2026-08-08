"""Parse helpers for portfolio snapshot include flags (续十六)."""

from __future__ import annotations


def _parse_include(raw: str | None) -> set[str]:
    return {part.strip() for part in (raw or "").lower().split(",") if part.strip()}


def test_parse_include_flags() -> None:
    assert _parse_include("risk_budget,optimize_summary") == {"risk_budget", "optimize_summary"}
    assert "risk" in _parse_include("risk")
    assert _parse_include(None) == set()
    assert _parse_include("  ") == set()
