"""Tests for FastAPI market sidecar (mocked upstream)."""

from __future__ import annotations

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient


@pytest.fixture
def client(monkeypatch):
    from sidecar.market import main as sidecar_main

    async def _fake_fetch(path: str):
        if "quotes" in path:
            return {"data": {"stocks": [{"symbol": "600519", "price": 1800.0}]}}
        return {}

    monkeypatch.setattr(sidecar_main, "_fetch_json", _fake_fetch)
    return TestClient(sidecar_main.app)


def test_price_endpoint(client):
    resp = client.get("/price/600519?market=CN")
    assert resp.status_code == 200
    body = resp.json()
    assert body["symbol"] == "600519"
    assert body["quote"]["symbol"] == "600519"


def test_health_reports_upstream_flag(monkeypatch):
    import httpx

    from sidecar.market import main as sidecar_main

    class _FailClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def get(self, url):
            raise httpx.ConnectError("upstream down")

    monkeypatch.setattr(sidecar_main.httpx, "AsyncClient", _FailClient)
    client = TestClient(sidecar_main.app)
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["upstream_ok"] is False
