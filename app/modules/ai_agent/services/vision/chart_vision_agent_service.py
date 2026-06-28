"""Chart Vision Agent Service — integrates vision pipeline for research graph (10.0)."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class ChartVisionAgentService:
    """Service that combines chart rendering, vision LLM, and pattern detection.

    This service provides the "eyes" for the research graph, allowing agents
    to visually analyze market charts alongside numerical analysis.
    """

    def __init__(
        self,
        *,
        stock_service: Any | None = None,
        vision_analyzer: Any | None = None,
        pattern_detector: Any | None = None,
    ):
        self._stock_service = stock_service
        self._vision_analyzer = vision_analyzer
        self._pattern_detector = pattern_detector

    def _get_vision_analyzer(self) -> Any:
        if self._vision_analyzer is not None:
            return self._vision_analyzer
        from app.infrastructure.vision.vision_analyzer import VisionAnalyzer
        self._vision_analyzer = VisionAnalyzer()
        return self._vision_analyzer

    def _get_pattern_detector(self) -> Any:
        if self._pattern_detector is not None:
            return self._pattern_detector
        from app.infrastructure.vision.pattern_detector import PatternDetector
        self._pattern_detector = PatternDetector()
        return self._pattern_detector

    def analyze(
        self,
        symbol: str,
        market: str = "CN",
        *,
        days: int = 120,
        indicators: list[str] | None = None,
        include_image: bool = False,
    ) -> dict[str, Any]:
        """Full visual analysis pipeline for a symbol.

        1. Fetch historical bar data
        2. Render K-line chart image
        3. Analyze chart with vision LLM
        4. Detect patterns numerically
        5. Merge and return comprehensive result

        Args:
            symbol: Stock symbol
            market: Market code (CN/US/HK)
            days: Number of trading days to analyze
            indicators: Technical indicators to overlay (ma5, ma10, ma20, ma60)
            include_image: Whether to include base64 image in response

        Returns:
            Comprehensive visual analysis result
        """
        if self._stock_service is None:
            return {
                "status": "error",
                "symbol": symbol,
                "message": "Stock service not configured",
            }

        from app.infrastructure.vision.chart_renderer import ChartRenderer

        renderer = ChartRenderer()
        render_result = renderer.render_from_service(
            self._stock_service,
            symbol,
            market,
            days=days,
            indicators=indicators or ["ma5", "ma20", "ma60"],
        )

        if render_result.get("status") != "success":
            return {
                "status": "error",
                "symbol": symbol,
                "message": f"Chart rendering failed: {render_result.get('message', 'unknown')}",
            }

        image_b64 = render_result.get("image_base64")
        analyzer = self._get_vision_analyzer()
        vision_result = analyzer.analyze_chart_image(
            image_base64=image_b64,
            symbol=symbol,
        )

        bars = self._fetch_bars(symbol, market, days)
        detector = self._get_pattern_detector()
        pattern_result = detector.detect_patterns(
            bars,
            vision_analysis=vision_result if vision_result.get("status") == "success" else None,
        )

        result = {
            "status": "success",
            "symbol": symbol,
            "market": market,
            "chart": {
                "bar_count": render_result.get("bar_count"),
                "date_range": render_result.get("date_range"),
                "image_size_bytes": render_result.get("image_size_bytes"),
            },
            "visual_analysis": {
                "trend": vision_result.get("trend", "unknown"),
                "patterns": vision_result.get("patterns", []),
                "support_levels": vision_result.get("support_levels", []),
                "resistance_levels": vision_result.get("resistance_levels", []),
                "overall_signal": vision_result.get("overall_signal", "neutral"),
                "confidence": vision_result.get("confidence", 0),
                "reasoning": vision_result.get("reasoning", ""),
            },
            "numerical_analysis": {
                "trend": pattern_result.get("trend", "unknown"),
                "patterns": pattern_result.get("patterns", []),
                "support_levels": pattern_result.get("support_levels", []),
                "resistance_levels": pattern_result.get("resistance_levels", []),
                "volatility": pattern_result.get("volatility", {}),
                "volume_trend": pattern_result.get("volume_trend", {}),
                "overall_signal": pattern_result.get("overall_signal", "neutral"),
                "confidence": pattern_result.get("confidence", 0),
            },
            "merged_signal": self._merge_signals(vision_result, pattern_result),
        }

        if include_image:
            result["chart"]["image_base64"] = image_b64

        return result

    def analyze_from_bars(
        self,
        bars: list[dict[str, Any]],
        *,
        symbol: str = "",
    ) -> dict[str, Any]:
        """Analyze from pre-fetched bar data (for research graph integration).

        Args:
            bars: OHLCV bar data
            symbol: Stock symbol for context

        Returns:
            Pattern detection result
        """
        if not bars:
            return {"status": "error", "message": "No bar data provided"}

        from app.infrastructure.vision.chart_renderer import ChartRenderer

        renderer = ChartRenderer()
        render_result = renderer.render_kline(bars, symbol=symbol)

        vision_result = {}
        if render_result.get("status") == "success":
            analyzer = self._get_vision_analyzer()
            vision_result = analyzer.analyze_chart_image(
                image_base64=render_result.get("image_base64"),
                symbol=symbol,
            )

        detector = self._get_pattern_detector()
        pattern_result = detector.detect_patterns(
            bars,
            vision_analysis=vision_result if vision_result.get("status") == "success" else None,
        )

        return {
            "status": "success",
            "symbol": symbol,
            "bar_count": len(bars),
            "patterns": pattern_result,
            "vision": vision_result if vision_result.get("status") == "success" else {},
        }

    def _fetch_bars(self, symbol: str, market: str, days: int) -> list[dict[str, Any]]:
        """Fetch historical bars from stock service."""
        from datetime import date, timedelta

        end_date = date.today()
        start_date = end_date - timedelta(days=int(days * 1.6))

        try:
            bars = self._stock_service.get_history(
                symbol, market, start_date.isoformat(), end_date.isoformat()
            )
            return bars or []
        except Exception as exc:
            logger.warning("Failed to fetch bars for %s: %s", symbol, exc)
            return []

    @staticmethod
    def _merge_signals(vision: dict[str, Any], numerical: dict[str, Any]) -> dict[str, Any]:
        """Merge vision LLM and numerical analysis signals."""
        v_signal = vision.get("overall_signal", "neutral")
        n_signal = numerical.get("overall_signal", "neutral")
        v_conf = float(vision.get("confidence", 0))
        n_conf = float(numerical.get("confidence", 0))

        signal_scores = {
            "strong_bullish": 2.0,
            "bullish": 1.0,
            "neutral": 0.0,
            "bearish": -1.0,
            "strong_bearish": -2.0,
        }

        v_score = signal_scores.get(v_signal, 0)
        n_score = signal_scores.get(n_signal, 0)

        total_conf = v_conf + n_conf
        if total_conf > 0:
            merged_score = (v_score * v_conf + n_score * n_conf) / total_conf
        else:
            merged_score = (v_score + n_score) / 2

        if merged_score >= 1.5:
            merged_signal = "strong_bullish"
        elif merged_score >= 0.5:
            merged_signal = "bullish"
        elif merged_score <= -1.5:
            merged_signal = "strong_bearish"
        elif merged_score <= -0.5:
            merged_signal = "bearish"
        else:
            merged_signal = "neutral"

        merged_confidence = round(min(1.0, (v_conf + n_conf) / 2), 2)

        return {
            "signal": merged_signal,
            "confidence": merged_confidence,
            "vision_signal": v_signal,
            "numerical_signal": n_signal,
            "vision_confidence": v_conf,
            "numerical_confidence": n_conf,
            "agreement": v_signal == n_signal,
        }


__all__ = ["ChartVisionAgentService"]
