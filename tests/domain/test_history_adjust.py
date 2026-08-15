from __future__ import annotations

from app.domain.shared.history_adjust import normalize_adjust, try_local_cn_history


def test_normalize_adjust_aliases() -> None:
    assert normalize_adjust("qfq") == "qfq"
    assert normalize_adjust("前复权") == "qfq"
    assert normalize_adjust("hfq") == "hfq"
    assert normalize_adjust("bfq") == "raw"
    assert normalize_adjust("none") == "raw"
    assert normalize_adjust(None) == "qfq"


def test_try_local_cn_history_returns_meta_when_missing_tdx() -> None:
    bars, meta = try_local_cn_history("600519", "2024-01-01", "2024-02-01", "qfq")
    assert isinstance(bars, list)
    assert meta["adjust"] == "qfq"
    assert "adjust_applied" in meta
