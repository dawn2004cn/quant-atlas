"""Unit tests for smoke_benchmark (no live server)."""

from __future__ import annotations

from scripts.perf.smoke_benchmark import _percentile, run_benchmark


def test_percentile_empty():
    assert _percentile([], 99) == 0.0


def test_percentile_single_value():
    assert _percentile([42.0], 50) == 42.0
    assert _percentile([42.0], 99) == 42.0


def test_run_benchmark_structure(monkeypatch):
    def fake_probe(url: str, timeout: float):
        return 10.0, 200, None

    monkeypatch.setattr("scripts.perf.smoke_benchmark._probe", fake_probe)
    report = run_benchmark(host="http://test", rounds=3, timeout=1.0)

    assert report["rounds"] == 3
    assert len(report["endpoints"]) == 4
    assert report["decision"]["async_optimization_recommended"] is False
    assert report["endpoints"][0]["p50_ms"] == 10.0
