"""Backtest loaders must not introduce look-ahead via auto-adjusted prices."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from app.infrastructure.agent.backtest.loaders import yfinance_loader as yf_mod


def test_yfinance_download_disables_auto_adjust() -> None:
    with patch.object(yf_mod, "yf") as mock_yf:
        mock_yf.download.return_value = MagicMock(empty=True)
        yf_mod._download_history("AAPL", "2024-01-01", "2024-12-31", "1d")
        mock_yf.download.assert_called_once()
        assert mock_yf.download.call_args.kwargs.get("auto_adjust") is False
