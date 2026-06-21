#!/usr/bin/env python3
"""Quick API smoke checks against the Flask app factory."""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from app.bootstrap import create_app


if __name__ == "__main__":
    app = create_app()
    client = app.test_client()

    print("--- Verify API connectivity ---")
    r_health = client.get("/api/v1/health")
    print(f"Health Status: {r_health.status_code} -> {r_health.get_json()}")

    r_panorama = client.get("/api/v1/markets/CN/panorama")
    print(f"Panorama Status: {r_panorama.status_code}")
    if r_panorama.status_code == 200:
        data = r_panorama.get_json()
        print(f"Panorama Data Keys: {list(data['data'].keys())}")
        print(f"Market Stats: Up={data['data'].get('up')}, Down={data['data'].get('down')}")
    else:
        print(f"Panorama Error Body: {r_panorama.get_data(as_text=True)[:200]}")

    print("\n--- Verify history endpoint ---")
    r_history = client.get("/api/v1/stocks/CN/600519/history?start=2024-01-01&end=2024-04-01")
    print(f"History Status: {r_history.status_code}")
    if r_history.status_code == 200:
        h_data = r_history.get_json()
        print(f"History Count: {len(h_data.get('data', []))}")
