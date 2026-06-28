from __future__ import annotations
"""High-performance technical indicator provider using Rust."""


import math
from typing import Any

import quant_core

from ...domain.ports import IndicatorProvider

import time
import logging
from app.core.metrics import RUST_INDICATOR_LATENCY, INDICATOR_ERRORS

class RustIndicatorProvider(IndicatorProvider):
    """Use the Rust 'quant_core' library for ultra-fast indicator calculation."""

    def calculate(self, history: list[dict[str, Any]]) -> dict[str, Any]:
        if not history:
            return {}

        try:
            closes = [float(r.get("close") or r.get("Close") or 0) for r in history]
            if len(closes) < 26:
                return {}

            res = {}

            # Helper for timing
            def _time_rust(name, func, *args):
                start = time.perf_counter()
                val = func(*args)
                RUST_INDICATOR_LATENCY.labels(indicator_type=name).observe(time.perf_counter() - start)
                return val

            # SMA 20
            sma20 = _time_rust("sma20", quant_core.calculate_sma, closes, 20)
            res["ma20"] = sma20[-1]

            # EMA 12/26
            ema12 = _time_rust("ema12", quant_core.calculate_ema, closes, 12)
            ema26 = _time_rust("ema26", quant_core.calculate_ema, closes, 26)
            res["ema12"] = ema12[-1]
            res["ema26"] = ema26[-1]

            # MACD (from EMA12/EMA26 already computed above)
            dif = [e12 - e26 for e12, e26 in zip(ema12, ema26)]
            dea = quant_core.calculate_ema(dif, 9)
            macd_hist = [d - s for d, s in zip(dif, dea)]
            res["macd"] = dif[-1]
            res["macd_signal"] = dea[-1]
            res["macd_diff"] = macd_hist[-1]

            # RSI (pure Python since not in quant_core)
            gains = [max(closes[i] - closes[i-1], 0) for i in range(1, len(closes))]
            losses = [max(closes[i-1] - closes[i], 0) for i in range(1, len(closes))]
            if len(gains) >= 14:
                avg_gain = sum(gains[-14:]) / 14
                avg_loss = sum(losses[-14:]) / 14
                rs = avg_gain / avg_loss if avg_loss != 0 else float("inf")
                res["rsi14"] = 100 - 100 / (1 + rs)
            else:
                res["rsi14"] = 50.0

            # Bollinger Bands (pure Python)
            window = 20
            if len(closes) >= window:
                sma_bb = sum(closes[-window:]) / window
                variance = sum((c - sma_bb) ** 2 for c in closes[-window:]) / window
                std_bb = math.sqrt(variance)
                res["bb_upper"] = sma_bb + 2.0 * std_bb
                res["bb_mid"] = sma_bb
                res["bb_lower"] = sma_bb - 2.0 * std_bb

            return {k: float(v) for k, v in res.items()}

        except Exception as e:
            INDICATOR_ERRORS.labels(provider="rust_core").inc()
            logging.getLogger(__name__).error(f"Rust indicator calculation failed: {e}")
            return {}
