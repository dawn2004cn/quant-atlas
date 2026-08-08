"""Tournament last-run API summary shaping."""

from __future__ import annotations

import json

from app.presentation.api.routes_v1_strategy_tournament import _summarize


def test_summarize_splits_accepted_rejected():
    payload = {
        "ok": True,
        "accepted": 1,
        "rejected": 1,
        "skipped": 0,
        "loaded": 2,
        "ts": "20260806T120000Z",
        "verdicts": [
            {"strategy_id": "a", "accepted": True, "reason": "ok", "sharpe": 2.0},
            {"strategy_id": "b", "accepted": False, "reason": "rejected:bias_gate_not_passed"},
        ],
    }
    out = _summarize(payload)
    assert out["summary"]["accepted"] == 1
    assert out["summary"]["rejected"] == 1
    assert out["accepted_rows"][0]["strategy_id"] == "a"
    assert "bias" in out["rejected_rows"][0]["reason"]


def test_tournament_run_writes_via_api_helper(tmp_path, monkeypatch):
    from app.tasks import strategy_tournament_tasks as tasks

    nl = tmp_path / "nl.jsonl"
    nl.write_text(
        '{"strategy_id":"nl.z","candidate_ready":true,"bias_passed":false,'
        '"preview_metrics":{"sharpe":2.0,"max_drawdown":0.05}}\n',
        encoding="utf-8",
    )
    runs = tmp_path / "runs"
    monkeypatch.setattr(tasks, "_nl_strategies_path", lambda: nl)
    monkeypatch.setattr(tasks, "_tournament_runs_dir", lambda: runs)
    result = tasks.run_strategy_tournament_tick(limit=5)
    summarized = _summarize(result)
    assert summarized["summary"]["rejected"] == 1  # bias not passed
    assert (runs / "latest.json").exists()
    raw = json.loads((runs / "latest.json").read_text(encoding="utf-8"))
    assert raw["rejected"] == 1
