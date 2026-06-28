from __future__ import annotations

"""Domain service for market analysis (Regime Analysis)."""


from typing import Any

import pandas as pd

from app.domain.services.regime_manager import MarketRegimeManager


class MarketAnalysisDomainService:
    """Pure domain service for market regime analysis."""

    def analyze_regime(
        self,
        index_history: list[dict[str, Any]],
        benchmark: str,
    ) -> dict[str, Any]:
        """Analyze market regime from index historical data."""
        if not index_history:
            return self._empty_sentiment(benchmark)

        try:
            df = pd.DataFrame(index_history)
            if "close" not in df.columns:
                return self._empty_sentiment(benchmark)

            df.rename(columns={"close": "Close"}, inplace=True)
            regime_mgr = MarketRegimeManager(df)

            return {
                "regime": regime_mgr.get_current_regime(),
                "recommended_categories": regime_mgr.get_recommended_categories(),
                "benchmark": benchmark,
                "analysis_at": pd.Timestamp.now().isoformat()
            }
        except Exception as e:
            return self._error_sentiment(benchmark, str(e))

    def _empty_sentiment(self, benchmark: str) -> dict[str, Any]:
        """Return empty sentiment when no data."""
        return {
            "regime": "未知",
            "recommended_categories": [],
            "benchmark": benchmark,
            "analysis_at": pd.Timestamp.now().isoformat(),
            "message": "暂无数据"
        }

    def _error_sentiment(self, benchmark: str, error: str) -> dict[str, Any]:
        """Return error sentiment when analysis fails."""
        return {
            "regime": "未知",
            "recommended_categories": [],
            "benchmark": benchmark,
            "analysis_at": pd.Timestamp.now().isoformat(),
            "message": f"分析失败: {error[:50]}"
        }
