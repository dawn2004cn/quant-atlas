"""cn_akshare_history adjust policy."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from app.infrastructure.providers import cn_akshare_history as mod


def test_fetch_cn_daily_hfq_uses_hfq_adjust() -> None:
    fake_df = MagicMock(empty=True)
    with patch.dict("sys.modules", {"akshare": MagicMock()}):
        import akshare as ak  # noqa: PLC0415

        ak.stock_zh_a_hist = MagicMock(return_value=fake_df)
        mod.fetch_cn_daily_hfq("600519", "2024-01-01", "2024-06-01")
        ak.stock_zh_a_hist.assert_called_once()
        assert ak.stock_zh_a_hist.call_args.kwargs["adjust"] == "hfq"
