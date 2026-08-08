"""Beat registration for Feature Pipeline v0."""

from app.celery_app import _build_beat_schedule


def test_feature_pipeline_beat_registered_when_enabled(monkeypatch):
    monkeypatch.setenv("FEATURE_PIPELINE_CELERY_BEAT", "1")
    schedule = _build_beat_schedule()
    assert "feature-pipeline-daily" in schedule
    entry = schedule["feature-pipeline-daily"]
    assert entry["task"] == "app.tasks.feature_pipeline_tasks.feature_pipeline_tick"


def test_feature_pipeline_beat_absent_by_default(monkeypatch):
    monkeypatch.setenv("FEATURE_PIPELINE_CELERY_BEAT", "0")
    schedule = _build_beat_schedule()
    assert "feature-pipeline-daily" not in schedule
