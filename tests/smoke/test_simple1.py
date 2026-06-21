"""Optional smoke tests against a running HTTP server.

Set ``RUN_E2E_HTTP=1`` to enable; otherwise this module collects no tests so
``pytest`` does not hit localhost during collection or default CI runs.
"""

from __future__ import annotations

import os

import pytest

pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_E2E_HTTP", "").strip() != "1",
    reason="Set RUN_E2E_HTTP=1 to run live-server smoke checks",
)


@pytest.mark.e2e
def test_simple1_endpoints_smoke() -> None:
    import requests

    base = os.environ.get("E2E_BASE_URL", "http://localhost:5000").rstrip("/")
    s = requests.Session()
    s.post(f"{base}/login", data={"username": "admin", "password": "admin123"}, timeout=10)

    endpoints = [
        "/api/v1/markets/CN/quotes?symbol=600519",
        "/api/v1/markets/CN/sentiment",
        "/api/v1/markets/pulse",
        "/api/v1/agent-swarm/capabilities",
        "/api/v1/agent-swarm/runs",
        "/api/v1/agent-swarm/experiments",
        "/api/v1/alpha-factory/status",
        "/api/v1/alpha-factory/pipeline",
        "/api/v1/alpha-factory/model-zoo",
        "/api/v1/alpha-factory/lineage",
        "/api/v1/daily-workbench",
        "/api/v1/recommendations/daily?market=CN",
        "/api/v1/stock-groups",
        "/api/v1/signal-observations",
        "/api/v1/user/page-preferences",
        "/api/v1/user/access-policy",
        "/api/v1/system/task-messages?limit=10",
        "/api/v1/research/pipeline-status",
        "/api/v1/global/quote?symbol=AAPL&market=US",
        "/api/v1/investment-managers",
        "/api/v1/moments",
        "/api/v1/integration/stack-status",
    ]

    ok = 0
    for ep in endpoints:
        r = s.get(base + ep, timeout=10)
        if r.status_code == 200:
            ok += 1

    # Do not require every route in all deployments; smoke = server responds.
    assert ok > 0, "no endpoints returned HTTP 200; check E2E_BASE_URL and credentials"
