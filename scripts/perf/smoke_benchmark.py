#!/usr/bin/env python3
"""Lightweight HTTP latency smoke test (no Locust required).

Writes JSON summary to instance/perf/smoke_benchmark.json for docs/perf_baseline.md.

Usage:
  python scripts/perf/smoke_benchmark.py
  python scripts/perf/smoke_benchmark.py --host http://127.0.0.1:5000 --rounds 30
"""

from __future__ import annotations

import argparse
import json
import statistics
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


@dataclass(frozen=True)
class EndpointSpec:
    name: str
    path: str


DEFAULT_ENDPOINTS = (
    EndpointSpec("system_health", "/system/health"),
    EndpointSpec("market_quotes", "/api/v1/markets/CN/quotes?symbol=600519&limit=1"),
    EndpointSpec("qlib_health", "/api/v1/qlib/health"),
    EndpointSpec("data_lake_health", "/api/v1/data-lake/health"),
)


def _percentile(samples: list[float], pct: float) -> float:
    if not samples:
        return 0.0
    ordered = sorted(samples)
    idx = max(0, min(len(ordered) - 1, int(round((pct / 100.0) * (len(ordered) - 1)))))
    return ordered[idx]


def _probe(url: str, timeout: float) -> tuple[float, int | None, str | None]:
    start = time.perf_counter()
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            _ = resp.read(256)
            elapsed_ms = (time.perf_counter() - start) * 1000.0
            return elapsed_ms, resp.status, None
    except urllib.error.HTTPError as exc:
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        return elapsed_ms, exc.code, str(exc.reason)
    except Exception as exc:  # noqa: BLE001 — benchmark boundary
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        return elapsed_ms, None, str(exc)


def run_benchmark_in_process(*, rounds: int) -> dict:
    """Measure latency via Flask test_client (no live server required)."""
    import os

    os.environ.setdefault("FLASK_ENV", "testing")
    from app import create_app

    app = create_app()
    client = app.test_client()

    report: dict = {
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "host": "in-process:test_client",
        "rounds": rounds,
        "endpoints": [],
        "decision": {"async_optimization_recommended": False, "reason": ""},
    }

    worst_p99 = 0.0
    worst_error_rate = 0.0

    with app.app_context():
        for spec in DEFAULT_ENDPOINTS:
            samples: list[float] = []
            errors = 0
            for _ in range(rounds):
                start = time.perf_counter()
                resp = client.get(spec.path)
                elapsed_ms = (time.perf_counter() - start) * 1000.0
                samples.append(elapsed_ms)
                if resp.status_code >= 400:
                    errors += 1

            error_rate = errors / rounds if rounds else 0.0
            p99 = _percentile(samples, 99)
            worst_p99 = max(worst_p99, p99)
            worst_error_rate = max(worst_error_rate, error_rate)

            report["endpoints"].append(
                {
                    "name": spec.name,
                    "path": spec.path,
                    "p50_ms": round(statistics.median(samples), 2) if samples else 0.0,
                    "p95_ms": round(_percentile(samples, 95), 2),
                    "p99_ms": round(p99, 2),
                    "error_rate": round(error_rate, 4),
                    "samples_ms": [round(x, 2) for x in samples[:5]],
                }
            )

    if worst_p99 > 500 or worst_error_rate > 0.005:
        report["decision"] = {
            "async_optimization_recommended": True,
            "reason": f"worst_p99_ms={worst_p99:.1f}, worst_error_rate={worst_error_rate:.4f}",
        }
    else:
        report["decision"] = {
            "async_optimization_recommended": False,
            "reason": f"within_threshold worst_p99_ms={worst_p99:.1f}",
        }

    return report


def run_benchmark(*, host: str, rounds: int, timeout: float) -> dict:
    host = host.rstrip("/")
    report: dict = {
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "host": host,
        "rounds": rounds,
        "endpoints": [],
        "decision": {"async_optimization_recommended": False, "reason": ""},
    }

    worst_p99 = 0.0
    worst_error_rate = 0.0

    for spec in DEFAULT_ENDPOINTS:
        samples: list[float] = []
        errors = 0
        for _ in range(rounds):
            ms, status, err = _probe(f"{host}{spec.path}", timeout)
            samples.append(ms)
            if err or (status is not None and status >= 400):
                errors += 1

        error_rate = errors / rounds if rounds else 0.0
        p99 = _percentile(samples, 99)
        worst_p99 = max(worst_p99, p99)
        worst_error_rate = max(worst_error_rate, error_rate)

        report["endpoints"].append(
            {
                "name": spec.name,
                "path": spec.path,
                "p50_ms": round(statistics.median(samples), 2) if samples else 0.0,
                "p95_ms": round(_percentile(samples, 95), 2),
                "p99_ms": round(p99, 2),
                "error_rate": round(error_rate, 4),
                "samples_ms": [round(x, 2) for x in samples[:5]],
            }
        )

    if worst_p99 > 500 or worst_error_rate > 0.005:
        report["decision"] = {
            "async_optimization_recommended": True,
            "reason": f"worst_p99_ms={worst_p99:.1f}, worst_error_rate={worst_error_rate:.4f}",
        }
    else:
        report["decision"] = {
            "async_optimization_recommended": False,
            "reason": f"within_threshold worst_p99_ms={worst_p99:.1f}",
        }

    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Quant Atlas HTTP smoke benchmark")
    parser.add_argument("--host", default="http://127.0.0.1:5000")
    parser.add_argument("--rounds", type=int, default=20)
    parser.add_argument("--timeout", type=float, default=10.0)
    parser.add_argument(
        "--in-process",
        action="store_true",
        help="Use Flask test_client instead of HTTP (no server required)",
    )
    parser.add_argument(
        "--out",
        default="instance/perf/smoke_benchmark.json",
        help="Output JSON path",
    )
    args = parser.parse_args()

    if args.in_process:
        report = run_benchmark_in_process(rounds=args.rounds)
    else:
        report = run_benchmark(host=args.host, rounds=args.rounds, timeout=args.timeout)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"\nWrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
