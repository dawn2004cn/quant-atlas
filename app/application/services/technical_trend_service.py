from __future__ import annotations
"""Technical trend analysis - application layer with pandas support.

This service delegates to the pure-domain ``TechnicalTrendService`` for
computation, accepting a pandas DataFrame and extracting the required
series (close, volume) before calling the domain logic.
"""


import logging
from typing import Any

import pandas as pd

from ...domain.analysis.technical_trend import TechnicalTrendService as PureTechnicalTrendService
from ...domain.entities import TrendAnalysisResult

logger = logging.getLogger(__name__)


class TechnicalTrendService:
    """
    Application-layer technical trend service.

    Accepts a pandas DataFrame (as the original API did) and delegates
    computation to the pure-domain ``TechnicalTrendService``.
    """

    def __init__(self) -> None:
        self._pure = PureTechnicalTrendService()

    def analyze(self, df: pd.DataFrame, code: str) -> TrendAnalysisResult:
        """Analyze stock trend from a pandas DataFrame.

        Parameters
        ----------
        df : pd.DataFrame
            Must contain 'close' and 'volume' columns (case-insensitive).
        code : str
            Stock symbol / identifier.

        Returns
        -------
        TrendAnalysisResult
        """
        if df is None or df.empty or len(df) < 20:
            logger.warning(f"{code} insufficient data for trend analysis")
            return TrendAnalysisResult(
                code=code,
                current_price=0.0,
                ma5=0.0,
                ma10=0.0,
                ma20=0.0,
                bias_ma5=0.0,
                trend_status="盘整",
                signals=["数据不足"],
            )

        # Normalise column names (case-insensitive)
        df = df.copy()
        col_map = {col.lower(): col for col in df.columns}
        close_col = col_map.get("close")
        volume_col = col_map.get("volume")
        if close_col is None or volume_col is None:
            logger.warning(f"{code} missing close/volume columns")
            return TrendAnalysisResult(
                code=code,
                current_price=0.0,
                ma5=0.0,
                ma10=0.0,
                ma20=0.0,
                bias_ma5=0.0,
                trend_status="盘整",
                signals=["数据不足"],
            )

        closes: list[float] = df[close_col].tolist()
        volumes: list[float] = df[volume_col].tolist()

        return self._pure.analyze(closes, volumes, code)
