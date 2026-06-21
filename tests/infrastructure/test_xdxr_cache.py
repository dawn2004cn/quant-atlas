"""xdxr process cache."""

from __future__ import annotations

import pandas as pd

from app.infrastructure.tdx_local import xdxr_cache


def test_xdxr_cache_reuses_fetcher(monkeypatch) -> None:
    xdxr_cache.clear_xdxr_cache()
    calls: list[tuple[str, str]] = []

    def _fetch(market: str, code: str) -> pd.DataFrame:
        calls.append((market, code))
        return pd.DataFrame({"fenhong": [0.1]}, index=pd.to_datetime(["2020-01-02"]))

    df1 = xdxr_cache.get_cached_xdxr("sh", "600519", _fetch)
    df2 = xdxr_cache.get_cached_xdxr("sh", "600519", _fetch)
    assert len(calls) == 1
    assert not df1.empty
    assert len(df2) == len(df1)
