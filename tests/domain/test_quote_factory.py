"""Canonical quote payload normalization."""

from __future__ import annotations

from app.domain.dto.quote_factory import (
    canonical_quote_payload,
    canonical_quote_list,
    canonical_panorama_dict,
)


def test_canonical_quote_payload_unifies_symbol_and_code():
    out = canonical_quote_payload(
        {"ticker": "600519", "pct_chg": 1.25, "change": 15.5, "name": "茅台"},
        market="CN",
    )
    assert out["code"] == "sh600519"
    assert out["symbol"] == "sh600519"
    assert out["code6"] == "600519"
    assert out["change_pct"] == 1.25
    assert out["change_amount"] == 15.5
    assert out["change"] == 15.5


def test_canonical_quote_payload_reads_chenge_typo():
    out = canonical_quote_payload({"code": "sz000001", "chenge": -2.5})
    assert out["change_pct"] == -2.5


def test_canonical_quote_list_normalizes_each_item():
    rows = canonical_quote_list(
        [{"ticker": "000001", "pct_chg": 1.0}, {"code": "600519", "change_pct": -0.5}],
        market="CN",
    )
    assert rows[0]["symbol"] == "sz000001"
    assert rows[1]["symbol"] == "sh600519"


def test_canonical_panorama_dict_normalizes_rankings():
    raw = {
        "market_status": "active",
        "gainers": [{"ticker": "300750", "pct_chg": 5.0, "name": "宁德"}],
        "losers": [{"code": "600519", "chenge": -1.2}],
    }
    out = canonical_panorama_dict(raw, market="CN")
    assert out["gainers"][0]["symbol"] == "sz300750"
    assert out["gainers"][0]["change_pct"] == 5.0
    assert out["losers"][0]["symbol"] == "sh600519"
    assert out["losers"][0]["change_pct"] == -1.2
    assert out["market"] == "CN"
