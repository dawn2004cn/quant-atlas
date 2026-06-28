from __future__ import annotations

import logging
import json
from typing import Any
from app.core.base_service import BaseApplicationService

logger = logging.getLogger(__name__)

class FastPathParameterStore(BaseApplicationService):
    """
    The FastPathParameterStore acts as the 'Short-Term Memory' for the Execution Path.
    It stores pre-computed parameters (like ATR, Risk Limits, and Model Weights)
    that the FastPathOrchestrator can read without triggering any AI reasoning.
    """

    def __init__(self, redis_client: Any = None):
        super().__init__()
        self._redis = redis_client
        self._local_cache: dict[str, Any] = {}

    def set_parameter(self, symbol: str, param_key: str, value: Any):
        """Update a parameter. Called by the Slow Path (AI/Analysis)."""
        key = f"fastpath:{symbol}:{param_key}"
        # 1. Update Local Cache for extreme speed
        if symbol not in self._local_cache:
            self._local_cache[symbol] = {}
        self._local_cache[symbol][param_key] = value

        # 2. Persist to Redis for cross-process consistency
        if self._redis:
            try:
                self._redis.set(key, json.dumps(value))
            except Exception as e:
                logger.error("FastPathStore Redis write failed: %s", e)

    def get_parameter(self, symbol: str, param_key: str, default: Any = None) -> Any:
        """Retrieve a parameter. Called by the Fast Path (Execution)."""
        # 1. Try local cache first
        if symbol in self._local_cache and param_key in self._local_cache[symbol]:
            return self._local_cache[symbol][param_key]

        # 2. Fallback to Redis
        if self._redis:
            try:
                val = self._redis.get(f"fastpath:{symbol}:{param_key}")
                if val:
                    parsed = json.loads(val)
                    # Backfill local cache
                    if symbol not in self._local_cache:
                        self._local_cache[symbol] = {}
                    self._local_cache[symbol][param_key] = parsed
                    return parsed
            except Exception as e:
                logger.debug("FastPathStore Redis read failed: %s", e)

        return default
