"""Tournament tick writes audit JSON."""

from __future__ import annotations

from pathlib import Path

from app.tasks.strategy_tournament_tasks import run_strategy_tournament_tick


def test_tournament_tick_writes_audit(tmp_path, monkeypatch):
    nl = tmp_path / "nl_strategies.jsonl"
    nl.write_text(
        '{"strategy_id":"nl.a","candidate_ready":true,"bias_passed":true,'
        '"preview_metrics":{"sharpe":2.0,"max_drawdown":0.05,"total_return":0.2}}\n',
        encoding="utf-8",
    )
    runs = tmp_path / "tournament_runs"

    monkeypatch.setattr(
        "app.tasks.strategy_tournament_tasks._nl_strategies_path",
        lambda: nl,
    )
    monkeypatch.setattr(
        "app.tasks.strategy_tournament_tasks._tournament_runs_dir",
        lambda: runs,
    )

    result = run_strategy_tournament_tick(limit=10)
    assert result["ok"] is True
    assert result["accepted"] == 1
    assert (runs / "latest.json").exists()
    assert "audit_path" in result
