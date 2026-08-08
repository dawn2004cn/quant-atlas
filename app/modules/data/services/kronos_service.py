from __future__ import annotations
"""Application service for Kronos foundation model predictions."""


import logging
import pandas as pd
from datetime import datetime
from typing import Any

from app.domain.ports import KronosRepository, KronosPredictorPort, MarketDataProvider
from app.domain.kronos_entities import KronosPrediction, KronosModel
from app.domain.enums import MarketCode
from app.core.logger import get_logger

logger = get_logger(__name__)


class KronosPredictionService:
    def __init__(
        self,
        repository: KronosRepository,
        predictor: KronosPredictorPort,
        market_data: MarketDataProvider
    ):
        self._repository = repository
        self._predictor = predictor
        self._market_data = market_data

    def predict_for_ticker(
        self,
        ticker: str,
        market: MarketCode,
        model_id: str = "Kronos-small",
        horizon_days: int = 5
    ) -> KronosPrediction:
        """Run Kronos prediction for a single ticker."""
        logger.info(f"Running Kronos prediction for {ticker} using {model_id}")
        
        # 1. Fetch historical data (e.g., last 400 points)
        # Using a fixed lookback for foundation model context
        history = self._market_data.get_stock_history(
            symbol=ticker,
            market=market,
            start="2020-01-01", # Actual start will be limited by provider
            end=datetime.now().strftime("%Y-%m-%d")
        )
        
        if not history:
            raise ValueError(f"No history found for {ticker}")

        df = pd.DataFrame(history)
        
        # 2. Run Kronos inference
        # pred_len mapping: 1 day = approx 48 * 5min intervals (if 5min model)
        # Simplified for MVP
        pred_len = horizon_days * 48 
        forecast_list = self._predictor.predict(df, model_id, pred_len=pred_len)
        
        # 3. Persist prediction
        prediction = KronosPrediction(
            ticker=ticker,
            model_id=model_id,
            prediction_date=datetime.now(),
            horizon_days=horizon_days,
            forecast_data=forecast_list
        )
        
        self._repository.save_prediction(prediction)
        return prediction

    def list_models(self) -> list[KronosModel]:
        return self._repository.list_active_models()

    def register_model(self, model: KronosModel) -> None:
        self._repository.save_model(model)
