from __future__ import annotations
"""AI prediction validation service."""


from datetime import datetime, timedelta

from app.core.logger import get_logger
from app.domain.enums import MarketCode
from app.domain.ports import MarketDataProvider
from app.domain.ports.analysis_report_port import AnalysisReportRepository

logger = get_logger(__name__)


class AnalysisPredictionService:
    """Validate AI historical predictions for accuracy."""

    def __init__(
        self,
        repo: AnalysisReportRepository,
        market_data: MarketDataProvider,
    ):
        self._repo = repo
        self._market_data = market_data

    async def validate_all_pending(self):
        """Scan all pending reports and compare with current market data."""
        pending = self._repo.get_pending_reports()
        logger.info(f"Found {len(pending)} pending reports for validation.")

        for report in pending:
            created_at = datetime.fromisoformat(report["created_at"])
            if datetime.now() - created_at < timedelta(hours=20):
                continue

            ticker = report["ticker"]
            old_price = report["market_price"]
            prediction = report["prediction_type"]

            try:
                quotes = self._market_data.get_realtime_quotes([ticker], MarketCode.CN)
                if not quotes:
                    continue

                current_price = quotes[0].price
                price_change_pct = (current_price - old_price) / old_price * 100

                score = 0.0
                if "买入" in prediction or "强烈买入" in prediction:
                    score = 1.0 if price_change_pct > 0.5 else (-1.0 if price_change_pct < -0.5 else 0.0)
                elif "卖出" in prediction or "强烈卖出" in prediction:
                    score = 1.0 if price_change_pct < -0.5 else (-1.0 if price_change_pct > 0.5 else 0.0)

                self._repo.update_validation(report["id"], score)
                logger.info(f"Validated {ticker}: prediction={prediction}, change={price_change_pct:.2f}%, score={score}")

            except Exception as e:
                logger.error(f"Failed to validate {ticker}: {e}")
