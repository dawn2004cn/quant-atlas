# Performance Baseline

## Scope

This baseline defines the API smoke path that must be measured before any synchronous I/O refactor is started.

No production optimization was applied because the repository does not yet have a measured P50/P95/P99 baseline for the target endpoints.

## Target endpoints

| Endpoint | Method | Purpose |
|---|---|---|
| `/system/health` | GET | System health (smoke_benchmark `system_health`) |
| `/api/v1/markets/CN/quotes` | GET | Market quotes batch (`market_quotes`) |
| `/api/v1/qlib/health` | GET | Qlib integration health |
| `/api/v1/data-lake/health` | GET | Unified data lake health |

## Lightweight smoke (recommended first)

```bash
# Live server (production-like HTTP stack)
python scripts/perf/smoke_benchmark.py --host http://127.0.0.1:5000 --rounds 20

# No server — in-process test_client (CI / local quick fill)
python scripts/perf/smoke_benchmark.py --in-process --rounds 20

python scripts/perf/update_baseline_doc.py
```

> **Note:** `--in-process` measures WSGI test_client latency only; use live `--host` before any async I/O optimization decision.

## Locust script (heavier)

```bash
python -m pip install locust
locust -f scripts/perf/locustfile.py --host http://127.0.0.1:5000 --headless -u 200 -r 20 -t 5m
```

## Current baseline

运行 `smoke_benchmark.py` 后由 `update_baseline_doc.py` 自动填表。服务未启动时先启动 Flask（`0.0.0.0:5000`），或使用 `instance/perf/smoke_benchmark.example.json` 做 dry-run 预览。

| 端点 | P50 (ms) | P95 (ms) | P99 (ms) | 错误率 | 日期 |
|------|----------|----------|----------|--------|------|
| `/system/health` | 2044.43 | 2062.22 | 2279.86 | 100.00% | 2026-06-15 |
| `/api/v1/markets/CN/quotes?symbol=600519&limit=1` | 2042.87 | 2063.94 | 2068.97 | 100.00% | 2026-06-15 |
| `/api/v1/qlib/health` | 2043.13 | 2051.65 | 2059.81 | 100.00% | 2026-06-15 |
| `/api/v1/data-lake/health` | 2044.8 | 2058.95 | 2063.8 | 100.00% | 2026-06-15 |

## Optimization gate

Only optimize synchronous market/AI I/O after a run shows:

- P99 > 500ms, or
- error rate > 0.5%, or
- health/workbench endpoint failure under 200 users.

## Success criteria

```bash
test -f scripts/perf/locustfile.py
locust -f scripts/perf/locustfile.py --headless -u 200 -r 20 -t 5m
```

The optimization gate must be decided from the measured P50/P95/P99 and error rate.
