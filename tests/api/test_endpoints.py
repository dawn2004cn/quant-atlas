"""Test API endpoints."""
from __future__ import annotations

import os

import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
import pytest

pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_E2E_HTTP", "").strip() != "1",
    reason="Requires running HTTP server at 127.0.0.1:5000",
)

BASE_URL = "http://127.0.0.1:5000"

ENDPOINTS = [
    ("/api/v1/health", "GET"),
    ("/api/v1/global/quote?symbol=AAPL&market=US", "GET"),
    ("/api/v1/global/history?symbol=AAPL&market=US", "GET"),
    ("/api/v1/markets/CN/quotes?symbol=300476&limit=5", "GET"),
    ("/api/v1/markets/CN/panorama", "GET"),
    ("/api/v1/quotes?symbol=sh000001&market=CN", "GET"),
    ("/api/v1/stocks/search?q=茅台&market=CN", "GET"),
    ("/api/v1/system/task-messages?limit=10", "GET"),
    ("/api/v1/strategy/recommend?symbol=300476&market=CN", "GET"),
]


def test_endpoint(endpoint, method="GET"):
    try:
        url = BASE_URL + endpoint
        resp = requests.request(method, url, timeout=10)
        status = resp.status_code
        return (endpoint, status, "OK" if status < 400 else f"FAIL({status})")
    except Exception as e:
        return (endpoint, 0, f"ERROR: {e}")


def main():
    print("Testing key API endpoints...\n")
    results = []
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(test_endpoint, e, m): (e, m) for e, m in ENDPOINTS}
        for future in as_completed(futures):
            results.append(future.result())

    for endpoint, status, result in sorted(results):
        print(f"{status:>6} {result:<20} {endpoint}")

    success = sum(1 for _, s, r in results if s < 400)
    print(f"\n{success}/{len(results)} endpoints passed")


if __name__ == "__main__":
    main()
