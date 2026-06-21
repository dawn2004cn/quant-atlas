from __future__ import annotations
"""Kronos implementation of KronosPredictorPort."""


import os
import sys
import pandas as pd
from typing import Any

from app.domain.ports import KronosPredictorPort
from app.config import BASE_DIR

# Add Kronos root to sys.path to allow importing its modules
KRONOS_ROOT = os.path.join(BASE_DIR, "Kronos")
if KRONOS_ROOT not in sys.path:
    sys.path.append(KRONOS_ROOT)


class KronosPredictorAdapter(KronosPredictorPort):
    def __init__(self, models_cache_dir: str | None = None):
        self._models_cache_dir = models_cache_dir
        self._loaded_predictors = {}

    def _get_predictor(self, model_id: str):
        if model_id in self._loaded_predictors:
            return self._loaded_predictors[model_id]

        # Dynamic import to avoid heavy dependency loading if not used
        try:
            from model import Kronos, KronosTokenizer, KronosPredictor
        except ImportError:
            raise RuntimeError("Kronos modules not found. Ensure Kronos directory is correctly placed.")

        # In a real scenario, we'd look up model_id to get hf_path or local_path
        # For this port, we assume model_id refers to a HF path or we use a default
        hf_model_path = model_id if "/" in model_id else f"NeoQuasar/{model_id}"
        tokenizer_path = "NeoQuasar/Kronos-Tokenizer-base" # Default
        
        tokenizer = KronosTokenizer.from_pretrained(tokenizer_path)
        model = Kronos.from_pretrained(hf_model_path)
        predictor = KronosPredictor(model, tokenizer, max_context=512)
        
        self._loaded_predictors[model_id] = predictor
        return predictor

    def predict(
        self,
        df: pd.DataFrame,
        model_id: str,
        pred_len: int = 120
    ) -> list[dict[str, Any]]:
        predictor = self._get_predictor(model_id)
        
        # Prepare timestamps as required by KronosPredictor
        # Assuming df has a 'timestamps' column or index
        if 'timestamps' in df.columns:
            x_timestamp = df['timestamps']
        else:
            x_timestamp = pd.to_datetime(df.index)

        # Generate future timestamps (simple business day or minute freq)
        # In a production app, we would use a proper calendar
        last_ts = x_timestamp.iloc[-1]
        y_timestamp = pd.date_range(start=last_ts, periods=pred_len + 1, freq='5min')[1:]

        # Select required columns
        x_df = df[['open', 'high', 'low', 'close', 'volume', 'amount']]

        pred_df = predictor.predict(
            df=x_df,
            x_timestamp=x_timestamp,
            y_timestamp=y_timestamp,
            pred_len=pred_len,
            sample_count=1
        )

        # Convert pred_df to list of dicts
        pred_df['timestamp'] = pred_df.index
        return pred_df.to_dict('records')

    def batch_predict(self, symbols: list[str], horizon: int = 20) -> list[dict[str, Any]]:
        results = []
        for symbol in symbols:
            results.append({"symbol": symbol, "status": "pending", "predictions": []})
        return results

    def predict_by_symbol(self, symbol: str, horizon: int = 20) -> dict[str, Any]:
        return {"symbol": symbol, "status": "pending", "predictions": []}
