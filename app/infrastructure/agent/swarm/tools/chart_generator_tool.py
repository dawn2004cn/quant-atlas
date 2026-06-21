from __future__ import annotations
"""Chart Generator Tool: market charts for Agent visual analysis."""

from datetime import date, timedelta
from pathlib import Path
from typing import Any

import pandas as pd

from app.core.logger import get_logger
from app.infrastructure.agent.swarm.tools_base import BaseTool

logger = get_logger(__name__)


def _bars_to_ohlcv_df(bars: list[dict[str, Any]]) -> pd.DataFrame:
    rows = []
    for bar in bars:
        rows.append(
            {
                "Open": float(bar["open"]),
                "High": float(bar["high"]),
                "Low": float(bar["low"]),
                "Close": float(bar["close"]),
                "Volume": float(bar.get("volume") or 0),
            },
        )
    df = pd.DataFrame(rows)
    df.index = pd.to_datetime([b["date"] for b in bars])
    return df


def _load_symbol_ohlcv(symbol: str, *, days: int = 120) -> pd.DataFrame | None:
    from app.infrastructure.providers.cn_akshare_history import fetch_cn_daily_hfq

    end = date.today().isoformat()
    start = (date.today() - timedelta(days=days)).isoformat()
    code = "".join(c for c in str(symbol) if c.isdigit())[-6:].zfill(6)
    bars, status = fetch_cn_daily_hfq(code, start, end)
    if not bars:
        logger.warning("chart_generator no bars for %s (%s)", code, status)
        return None
    return _bars_to_ohlcv_df(bars)


class ChartGeneratorTool(BaseTool):
    """Generates market charts from stock data for visual inspection."""

    name = "chart_generator"
    description = "Generate a K-line chart image for a specific stock and date range."
    is_readonly = False
    parameters = {
        "type": "object",
        "properties": {
            "symbol": {"type": "string", "description": "Stock symbol."},
            "filename": {"type": "string", "description": "Output image filename."},
        },
        "required": ["symbol", "filename"],
    }

    def execute(self, **kwargs: Any) -> str:
        symbol = kwargs["symbol"]
        filename = kwargs["filename"]
        run_dir = kwargs.get("run_dir", ".")

        output_path = Path(run_dir) / filename

        try:
            df = _load_symbol_ohlcv(symbol)
            if df is None or df.empty:
                return f"Error generating chart: no market data for {symbol}"

            import mplfinance as mpf  # noqa: PLC0415

            mpf.plot(df, type="candle", volume=True, savefig=str(output_path))
            return f"Chart for {symbol} saved to {output_path} ({len(df)} bars)."
        except Exception as exc:  # noqa: BLE001
            logger.error("Chart generation failed: %s", exc, exc_info=True)
            return f"Error generating chart: {exc!s}"
