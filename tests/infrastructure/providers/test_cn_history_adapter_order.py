"""CN history chain must prefer Tongdaxin daily bars."""

from __future__ import annotations


def test_cn_history_adapters_tdx_first():
    from app.infrastructure.providers.history_adapters import _build_cn_history_adapters

    names = [name for name, _ in _build_cn_history_adapters()]
    assert names[:2] == ["tdx_file", "tdx_tcp"]
    assert names.index("tdx_file") < names.index("timescale")
    assert names.index("tdx_tcp") < names.index("akshare")
