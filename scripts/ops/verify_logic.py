#!/usr/bin/env python3
"""Quick provider-level logic checks for local debugging."""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from app.domain.enums import MarketCode
from app.infrastructure.providers.market_data import MultiSourceMarketProvider


if __name__ == "__main__":
    print("--- 1. Verify provider init ---")
    provider = MultiSourceMarketProvider()
    print("Provider OK")

    print("\n--- 2. Verify market overview ---")
    panorama = provider.get_market_overview(MarketCode.CN)
    print(f"Panorama Results: {panorama}")

    print("\n--- 3. Verify history fetch ---")
    history = provider.get_stock_history("600519", MarketCode.CN, "2024-01-01", "2024-04-01")
    print(f"History records found: {len(history)}")
    if history:
        print(f"Sample: {history[0]}")

    print("\n--- Verification complete ---")
