"""Beat registration for strategy tournament."""

from app.celery_app import _build_beat_schedule


def test_tournament_beat_registered_when_enabled(monkeypatch):
    monkeypatch.setenv("STRATEGY_TOURNAMENT_CELERY_BEAT", "1")
    schedule = _build_beat_schedule()
    assert "strategy-tournament-evening" in schedule
    entry = schedule["strategy-tournament-evening"]
    assert entry["task"] == "app.tasks.strategy_tournament_tasks.strategy_tournament_tick"


def test_tournament_beat_absent_by_default(monkeypatch):
    monkeypatch.setenv("STRATEGY_TOURNAMENT_CELERY_BEAT", "0")
    schedule = _build_beat_schedule()
    assert "strategy-tournament-evening" not in schedule
