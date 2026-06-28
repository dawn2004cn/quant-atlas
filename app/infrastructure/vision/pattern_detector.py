"""Pattern Detector — combines numerical TA with vision LLM for structured pattern detection."""

from __future__ import annotations

import logging
import math
from typing import Any

logger = logging.getLogger(__name__)


class PatternDetector:
    """Detects chart patterns using numerical analysis, enhanced by vision LLM.

    Combines traditional technical analysis (support/resistance, trend detection)
    with vision LLM pattern recognition for comprehensive analysis.
    """

    def detect_patterns(
        self,
        bars: list[dict[str, Any]],
        *,
        vision_analysis: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Detect patterns from bar data, optionally merging vision LLM results.

        Args:
            bars: OHLCV bar data
            vision_analysis: Optional vision LLM analysis to merge

        Returns:
            Structured pattern detection result
        """
        if not bars or len(bars) < 10:
            return {
                "status": "insufficient_data",
                "bar_count": len(bars),
                "patterns": [],
                "trend": "unknown",
                "support_levels": [],
                "resistance_levels": [],
            }

        closes = [float(b.get("close") or b.get("Close") or 0) for b in bars]
        highs = [float(b.get("high") or b.get("High") or 0) for b in bars]
        lows = [float(b.get("low") or b.get("Low") or 0) for b in bars]
        volumes = [float(b.get("volume") or b.get("Volume") or 0) for b in bars]

        closes = [c for c in closes if c > 0]
        highs = [h for h in highs if h > 0]
        lows = [l for l in lows if l > 0]

        if len(closes) < 10:
            return {
                "status": "insufficient_data",
                "bar_count": len(closes),
                "patterns": [],
                "trend": "unknown",
            }

        trend = self._detect_trend(closes)
        support = self._find_support_levels(lows, closes)
        resistance = self._find_resistance_levels(highs, closes)
        ma_cross = self._detect_ma_crossover(closes)
        volatility = self._compute_volatility(closes)
        volume_trend = self._analyze_volume(volumes)

        numerical_patterns = []
        if ma_cross:
            numerical_patterns.append(ma_cross)

        volatility_pattern = self._volatility_pattern(volatility, closes)
        if volatility_pattern:
            numerical_patterns.append(volatility_pattern)

        reversal = self._detect_reversal(closes, highs, lows)
        if reversal:
            numerical_patterns.append(reversal)

        all_patterns = numerical_patterns
        if vision_analysis and vision_analysis.get("patterns"):
            for vp in vision_analysis["patterns"]:
                all_patterns.append({
                    "name": vp.get("name", "unknown"),
                    "confidence": float(vp.get("confidence", 0)),
                    "source": "vision_llm",
                    "description": vp.get("description", ""),
                    "implication": vp.get("implication", "neutral"),
                })

        overall_signal = self._compute_overall_signal(
            trend, all_patterns, support, resistance
        )

        result = {
            "status": "success",
            "bar_count": len(bars),
            "trend": trend,
            "support_levels": support,
            "resistance_levels": resistance,
            "volatility": volatility,
            "volume_trend": volume_trend,
            "patterns": all_patterns,
            "overall_signal": overall_signal,
            "confidence": self._compute_confidence(all_patterns, trend),
        }

        if vision_analysis:
            result["vision_trend"] = vision_analysis.get("trend", "")
            result["vision_signal"] = vision_analysis.get("overall_signal", "")
            result["vision_confidence"] = vision_analysis.get("confidence", 0)

        return result

    def _detect_trend(self, closes: list[float]) -> str:
        """Detect trend direction using linear regression slope."""
        n = len(closes)
        if n < 5:
            return "unknown"

        x_mean = (n - 1) / 2.0
        y_mean = sum(closes) / n
        numerator = sum((i - x_mean) * (closes[i] - y_mean) for i in range(n))
        denominator = sum((i - x_mean) ** 2 for i in range(n))

        if denominator == 0:
            return "sideways"

        slope = numerator / denominator
        slope_pct = (slope / y_mean) * 100 if y_mean > 0 else 0

        short_closes = closes[-20:] if n >= 20 else closes
        short_change = (short_closes[-1] - short_closes[0]) / short_closes[0] * 100 if short_closes[0] > 0 else 0

        if slope_pct > 0.1 and short_change > 3:
            return "strong_uptrend"
        if slope_pct > 0.03:
            return "uptrend"
        if slope_pct < -0.1 and short_change < -3:
            return "strong_downtrend"
        if slope_pct < -0.03:
            return "downtrend"
        return "sideways"

    def _find_support_levels(self, lows: list[float], closes: list[float], n_levels: int = 3) -> list[float]:
        """Find support levels using local minima clustering."""
        if len(lows) < 10:
            return []

        window = max(3, len(lows) // 20)
        local_mins = []
        for i in range(window, len(lows) - window):
            if all(lows[i] <= lows[i - j] for j in range(1, window + 1)) and \
               all(lows[i] <= lows[i + j] for j in range(1, window + 1)):
                local_mins.append(lows[i])

        if not local_mins:
            recent_low = min(lows[-20:]) if len(lows) >= 20 else min(lows)
            return [round(recent_low, 2)]

        local_mins.sort()
        clusters: list[list[float]] = []
        threshold = (max(lows) - min(lows)) * 0.02

        for val in local_mins:
            placed = False
            for cluster in clusters:
                if abs(val - cluster[0]) < threshold:
                    cluster.append(val)
                    placed = True
                    break
            if not placed:
                clusters.append([val])

        clusters.sort(key=len, reverse=True)
        levels = [round(sum(c) / len(c), 2) for c in clusters[:n_levels] if c]
        return levels

    def _find_resistance_levels(self, highs: list[float], closes: list[float], n_levels: int = 3) -> list[float]:
        """Find resistance levels using local maxima clustering."""
        if len(highs) < 10:
            return []

        window = max(3, len(highs) // 20)
        local_maxs = []
        for i in range(window, len(highs) - window):
            if all(highs[i] >= highs[i - j] for j in range(1, window + 1)) and \
               all(highs[i] >= highs[i + j] for j in range(1, window + 1)):
                local_maxs.append(highs[i])

        if not local_maxs:
            recent_high = max(highs[-20:]) if len(highs) >= 20 else max(highs)
            return [round(recent_high, 2)]

        local_maxs.sort(reverse=True)
        clusters: list[list[float]] = []
        threshold = (max(highs) - min(highs)) * 0.02

        for val in local_maxs:
            placed = False
            for cluster in clusters:
                if abs(val - cluster[0]) < threshold:
                    cluster.append(val)
                    placed = True
                    break
            if not placed:
                clusters.append([val])

        clusters.sort(key=len, reverse=True)
        levels = [round(sum(c) / len(c), 2) for c in clusters[:n_levels] if c]
        return levels

    def _detect_ma_crossover(self, closes: list[float]) -> dict[str, Any] | None:
        """Detect moving average crossover signals."""
        if len(closes) < 20:
            return None

        ma5 = self._moving_average(closes, 5)
        ma20 = self._moving_average(closes, 20)

        if len(ma5) < 3 or len(ma20) < 3:
            return None

        offset = len(ma5) - len(ma20)
        prev_diff = ma5[-2 + offset] - ma20[-2] if len(ma5) >= 2 else 0
        curr_diff = ma5[-1] - ma20[-1]

        if prev_diff <= 0 < curr_diff:
            return {
                "name": "MA5/MA20 金叉",
                "confidence": 0.7,
                "source": "numerical",
                "description": "5日均线上穿20日均线，短期趋势转强",
                "implication": "bullish",
            }
        if prev_diff >= 0 > curr_diff:
            return {
                "name": "MA5/MA20 死叉",
                "confidence": 0.7,
                "source": "numerical",
                "description": "5日均线下穿20日均线，短期趋势转弱",
                "implication": "bearish",
            }
        return None

    def _compute_volatility(self, closes: list[float]) -> dict[str, Any]:
        """Compute volatility metrics."""
        if len(closes) < 10:
            return {"annualized": 0, "regime": "unknown"}

        returns = [(closes[i] - closes[i - 1]) / closes[i - 1] for i in range(1, len(closes)) if closes[i - 1] > 0]
        if not returns:
            return {"annualized": 0, "regime": "unknown"}

        mean_r = sum(returns) / len(returns)
        variance = sum((r - mean_r) ** 2 for r in returns) / len(returns)
        daily_vol = math.sqrt(variance)
        annualized = daily_vol * math.sqrt(252) * 100

        if annualized > 50:
            regime = "extreme_high"
        elif annualized > 30:
            regime = "high"
        elif annualized > 15:
            regime = "normal"
        else:
            regime = "low"

        return {
            "annualized": round(annualized, 2),
            "daily": round(daily_vol * 100, 3),
            "regime": regime,
        }

    def _analyze_volume(self, volumes: list[float]) -> dict[str, Any]:
        """Analyze volume trend."""
        if len(volumes) < 10:
            return {"trend": "unknown"}

        recent = volumes[-5:]
        earlier = volumes[-20:-5] if len(volumes) >= 20 else volumes[:-5]

        avg_recent = sum(recent) / len(recent) if recent else 0
        avg_earlier = sum(earlier) / len(earlier) if earlier else 0

        if avg_earlier == 0:
            return {"trend": "unknown"}

        ratio = avg_recent / avg_earlier
        if ratio > 1.5:
            return {"trend": "expanding", "ratio": round(ratio, 2), "description": "成交量显著放大"}
        if ratio > 1.1:
            return {"trend": "increasing", "ratio": round(ratio, 2), "description": "成交量温和放大"}
        if ratio < 0.7:
            return {"trend": "shrinking", "ratio": round(ratio, 2), "description": "成交量明显萎缩"}
        return {"trend": "stable", "ratio": round(ratio, 2), "description": "成交量平稳"}

    def _volatility_pattern(self, volatility: dict[str, Any], closes: list[float]) -> dict[str, Any] | None:
        """Detect volatility-based patterns."""
        regime = volatility.get("regime", "")
        if regime == "low" and len(closes) >= 20:
            recent_range = (max(closes[-20:]) - min(closes[-20:])) / closes[-20] * 100 if closes[-20] > 0 else 0
            if recent_range < 5:
                return {
                    "name": "缩量横盘（蓄势）",
                    "confidence": 0.5,
                    "source": "numerical",
                    "description": "低波动率+窄幅震荡，可能即将选择方向突破",
                    "implication": "neutral",
                }
        if regime in ("extreme_high", "high"):
            return {
                "name": "高波动率",
                "confidence": 0.6,
                "source": "numerical",
                "description": f"年化波动率 {volatility.get('annualized', 0):.1f}%，市场不确定性高",
                "implication": "bearish",
            }
        return None

    def _detect_reversal(self, closes: list[float], highs: list[float], lows: list[float]) -> dict[str, Any] | None:
        """Detect potential reversal patterns."""
        if len(closes) < 20:
            return None

        recent = closes[-5:]
        prior = closes[-20:-5]

        prior_trend = (prior[-1] - prior[0]) / prior[0] * 100 if prior[0] > 0 else 0
        recent_change = (recent[-1] - recent[0]) / recent[0] * 100 if recent[0] > 0 else 0

        if prior_trend < -10 and recent_change > 3:
            return {
                "name": "潜在底部反转",
                "confidence": 0.55,
                "source": "numerical",
                "description": f"前期下跌{prior_trend:.1f}%后近5日反弹{recent_change:.1f}%",
                "implication": "bullish",
            }
        if prior_trend > 10 and recent_change < -3:
            return {
                "name": "潜在顶部反转",
                "confidence": 0.55,
                "source": "numerical",
                "description": f"前期上涨{prior_trend:.1f}%后近5日回落{recent_change:.1f}%",
                "implication": "bearish",
            }
        return None

    def _compute_overall_signal(
        self,
        trend: str,
        patterns: list[dict[str, Any]],
        support: list[float],
        resistance: list[float],
    ) -> str:
        """Compute overall trading signal from all indicators."""
        score = 0.0

        if "uptrend" in trend:
            score += 1.5
        elif "downtrend" in trend:
            score -= 1.5

        for p in patterns:
            conf = float(p.get("confidence", 0))
            imp = p.get("implication", "neutral")
            if imp == "bullish":
                score += conf * 2
            elif imp == "bearish":
                score -= conf * 2

        if score >= 3:
            return "strong_bullish"
        if score >= 1:
            return "bullish"
        if score <= -3:
            return "strong_bearish"
        if score <= -1:
            return "bearish"
        return "neutral"

    def _compute_confidence(self, patterns: list[dict[str, Any]], trend: str) -> float:
        """Compute overall confidence score."""
        if not patterns and trend == "unknown":
            return 0.1
        if not patterns:
            return 0.4
        avg_conf = sum(float(p.get("confidence", 0)) for p in patterns) / len(patterns)
        trend_bonus = 0.1 if trend != "sideways" and trend != "unknown" else 0
        return min(1.0, round(avg_conf + trend_bonus, 2))

    @staticmethod
    def _moving_average(data: list[float], window: int) -> list[float]:
        """Compute simple moving average."""
        if len(data) < window:
            return []
        result = []
        for i in range(window - 1, len(data)):
            result.append(sum(data[i - window + 1:i + 1]) / window)
        return result


__all__ = ["PatternDetector"]
