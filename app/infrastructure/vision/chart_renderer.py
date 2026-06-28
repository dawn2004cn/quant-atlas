"""Chart Renderer — generates K-line chart images from real market data."""

from __future__ import annotations

import base64
import io
import logging
from datetime import date, timedelta
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class ChartRenderer:
    """Renders market data into chart images for visual analysis.

    Supports K-line (candlestick) charts with volume, moving averages,
    and other technical indicators.
    """

    def __init__(self, *, style: str = "charles", figsize: tuple[int, int] = (12, 8)):
        self._style = style
        self._figsize = figsize

    def render_kline(
        self,
        bars: list[dict[str, Any]],
        *,
        symbol: str = "",
        title: str | None = None,
        indicators: list[str] | None = None,
        output_path: Path | None = None,
    ) -> dict[str, Any]:
        """Render a K-line (candlestick) chart from OHLCV bar data.

        Args:
            bars: List of bar dicts with keys: date/open/high/low/close/volume
            symbol: Stock symbol for title
            title: Optional chart title override
            indicators: List of indicators to overlay (ma5, ma10, ma20, ma60)
            output_path: Optional file path to save the image

        Returns:
            Dict with image_base64, image_path (if saved), dimensions
        """
        try:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.dates as mdates
            import matplotlib.pyplot as plt
            import mplfinance as mpf
            import pandas as pd
        except ImportError as exc:
            logger.warning("matplotlib/mplfinance unavailable: %s", exc)
            return {"status": "error", "message": f"Chart libraries unavailable: {exc}"}

        if not bars:
            return {"status": "error", "message": "No bar data provided"}

        try:
            df = self._bars_to_dataframe(bars)
            if df.empty:
                return {"status": "error", "message": "Failed to parse bar data"}

            add_plots = self._build_indicator_plots(df, indicators or [])

            chart_title = title or f"{symbol} K-Line" if symbol else "K-Line Chart"

            save_kwargs: dict[str, Any] = {}
            if output_path:
                output_path.parent.mkdir(parents=True, exist_ok=True)
                save_kwargs["savefig"] = str(output_path)

            buf = io.BytesIO()
            save_kwargs.setdefault("savefig", buf)

            mpf.plot(
                df,
                type="candle",
                style=self._style,
                volume=True,
                title=chart_title,
                figsize=self._figsize,
                addplot=add_plots if add_plots else None,
                **save_kwargs,
            )

            result: dict[str, Any] = {
                "status": "success",
                "bar_count": len(df),
                "date_range": f"{df.index[0].strftime('%Y-%m-%d')} → {df.index[-1].strftime('%Y-%m-%d')}",
            }

            if output_path:
                result["image_path"] = str(output_path)

            buf.seek(0)
            image_bytes = buf.read()
            result["image_base64"] = base64.b64encode(image_bytes).decode("utf-8")
            result["image_size_bytes"] = len(image_bytes)

            plt.close("all")
            return result

        except Exception as exc:
            logger.error("Chart rendering failed: %s", exc)
            return {"status": "error", "message": str(exc)}

    def render_from_service(
        self,
        stock_service: Any,
        symbol: str,
        market: str = "CN",
        *,
        days: int = 120,
        indicators: list[str] | None = None,
        output_path: Path | None = None,
    ) -> dict[str, Any]:
        """Fetch real market data and render a chart.

        Args:
            stock_service: Service with get_history(symbol, market, start, end) method
            symbol: Stock symbol
            market: Market code (CN/US/HK)
            days: Number of trading days to fetch
            indicators: Technical indicators to overlay
            output_path: Optional output file path

        Returns:
            Chart rendering result dict
        """
        end_date = date.today()
        start_date = end_date - timedelta(days=int(days * 1.6))

        try:
            bars = stock_service.get_history(
                symbol, market, start_date.isoformat(), end_date.isoformat()
            )
        except Exception as exc:
            logger.error("Failed to fetch history for %s: %s", symbol, exc)
            return {"status": "error", "message": f"Data fetch failed: {exc}"}

        if not bars:
            return {"status": "error", "message": f"No data for {symbol}"}

        return self.render_kline(
            bars,
            symbol=symbol,
            indicators=indicators,
            output_path=output_path,
        )

    def _bars_to_dataframe(self, bars: list[dict[str, Any]]) -> Any:
        """Convert bar dicts to a pandas DataFrame with DatetimeIndex."""
        import pandas as pd

        rows = []
        for bar in bars:
            d = bar.get("date") or bar.get("Date") or bar.get("timestamp") or ""
            o = float(bar.get("open") or bar.get("Open") or 0)
            h = float(bar.get("high") or bar.get("High") or 0)
            l = float(bar.get("low") or bar.get("Low") or 0)
            c = float(bar.get("close") or bar.get("Close") or 0)
            v = float(bar.get("volume") or bar.get("Volume") or 0)
            if o <= 0 and c <= 0:
                continue
            if isinstance(d, str):
                try:
                    d = pd.Timestamp(d)
                except Exception:
                    continue
            rows.append({"Open": o, "High": h, "Low": l, "Close": c, "Volume": v, "Date": d})

        if not rows:
            return pd.DataFrame()

        df = pd.DataFrame(rows)
        df.set_index("Date", inplace=True)
        df.sort_index(inplace=True)
        return df

    def _build_indicator_plots(self, df: Any, indicators: list[str]) -> list:
        """Build mplfinance addplot objects for requested indicators."""
        import mplfinance as mpf

        plots = []
        ma_map = {
            "ma5": (5, "blue"),
            "ma10": (10, "orange"),
            "ma20": (20, "purple"),
            "ma60": (60, "green"),
        }
        for ind in indicators:
            ind_lower = ind.lower()
            if ind_lower in ma_map:
                window, color = ma_map[ind_lower]
                if len(df) >= window:
                    ma = df["Close"].rolling(window=window).mean()
                    plots.append(mpf.make_addplot(ma, color=color, width=0.8))
        return plots


__all__ = ["ChartRenderer"]
