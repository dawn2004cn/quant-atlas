#!/usr/bin/env python3
"""Sync legacy SQLite cache data into Redis."""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SCRIPTS_ROOT = _REPO_ROOT / "scripts"
for _path in (str(_REPO_ROOT), str(_SCRIPTS_ROOT)):
    if _path not in sys.path:
        sys.path.insert(0, _path)

from redis_cache import RedisCache
from stock_cache_db import StockCache


class DataSync:
    def __init__(self):
        self.sqlite_cache = StockCache()
        self.redis_cache = RedisCache()

    def sync_stocks(self):
        print("Starting stock sync...")
        stocks = self.sqlite_cache.get_all_stocks(max_age_minutes=1440)
        if stocks:
            print(f"Found {len(stocks)} stocks, syncing...")
            self.redis_cache.save_stocks(stocks)
            print(f"Done: synced {len(stocks)} stocks")
        else:
            print("No stock cache rows found")

    def sync_fund_flow(self):
        print("\nStarting fund flow sync...")
        try:
            cursor = self.sqlite_cache.conn.cursor()
            cursor.execute("SELECT code, main_in, retail_in, main_ratio, update_time FROM fund_flow")
            fund_data = cursor.fetchall()
            if fund_data:
                print(f"Found {len(fund_data)} fund flow rows, syncing...")
                for row in fund_data:
                    code, main_in, retail_in, main_ratio, _update_time = row
                    self.redis_cache.save_fund_flow(
                        code,
                        {"main_in": main_in, "retail_in": retail_in, "main_ratio": main_ratio},
                    )
                print(f"Done: synced {len(fund_data)} fund flow rows")
            else:
                print("No fund flow rows found")
        except Exception as exc:  # noqa: BLE001
            print(f"Fund flow sync failed: {exc}")

    def sync_lhb(self):
        print("\nLonghu cache sync is not implemented in RedisCache yet")

    def sync_tech_indicators(self):
        print("\nTech indicator sync is not implemented in RedisCache yet")

    def sync_fundamental_data(self):
        print("\nFundamental sync is not implemented in RedisCache yet")

    def sync_market_all_cache(self):
        print("\nStarting market-all cache sync...")
        try:
            market_data = self.sqlite_cache.get_market_all_cache()
            if market_data:
                self.redis_cache.save_market_all_cache(market_data)
                print("Done: synced market-all cache")
            else:
                print("No market-all cache rows found")
        except Exception as exc:  # noqa: BLE001
            print(f"Market-all cache sync failed: {exc}")

    def sync_stock_groups(self):
        print("\nStock group sync is not implemented in RedisCache yet")

    def sync_market_movements(self):
        print("\nMarket movement sync is not implemented in RedisCache yet")

    def sync_stock_selection_scores(self):
        print("\nStock selection score sync is not implemented in RedisCache yet")

    def sync_stock_selection_reports(self):
        print("\nStock selection report sync is not implemented in RedisCache yet")

    def run(self):
        print("=" * 60)
        print("Syncing SQLite data to Redis")
        print("=" * 60)
        try:
            self.sync_stocks()
            self.sync_fund_flow()
            self.sync_lhb()
            self.sync_tech_indicators()
            self.sync_fundamental_data()
            self.sync_market_all_cache()
            self.sync_stock_groups()
            self.sync_market_movements()
            self.sync_stock_selection_scores()
            self.sync_stock_selection_reports()
            print("\n" + "=" * 60)
            print("Sync complete")
            print("=" * 60)
        finally:
            self.sqlite_cache.close()
            self.redis_cache.close()


if __name__ == "__main__":
    DataSync().run()
