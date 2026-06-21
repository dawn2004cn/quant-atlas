"""Deprecated stub — use ``app.core.mesh.memory_fabric.MemoryFabric`` in production paths."""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any

from app.core.logger import get_logger

logger = get_logger(__name__)


class MemoryFabricStubClient:
    """[STUB] Placeholder vector-store client for offline demos and tests only."""

    def __init__(self, connection_params: dict[str, Any]) -> None:
        self._params = connection_params
        self.is_connected = True
        logger.debug("MemoryFabricStubClient initialized (stub)")

    @staticmethod
    def _deterministic_embedding(data_point: str, dimension: int = 128) -> list[float]:
        seed = sum(ord(c) for c in data_point[:64])
        return [((seed + i) % 997) / 997.0 for i in range(dimension)]

    async def connect_and_validate(self, _params: dict[str, Any]) -> bool:
        return self.is_connected

    async def ingest_memory(
        self,
        content: str,
        embeddings: list[float],
        metadata: dict[str, Any],
    ) -> str | None:
        if not self.is_connected:
            return None
        await asyncio.sleep(0)
        unique_id = f"stub_mem_{datetime.now().timestamp():.0f}_{hash(content) & 0xFFFF:x}"
        logger.debug("stub ingest id=%s meta_keys=%s dim=%s", unique_id[:12], list(metadata), len(embeddings))
        return unique_id

    async def query_semantic_memory(self, user_query: str, top_k: int = 3) -> list[dict[str, Any]]:
        if not self.is_connected:
            return []
        await asyncio.sleep(0)
        _ = self._deterministic_embedding(user_query)
        return [
            {
                "id": f"stub_mem_{i}",
                "score": round(0.9 - i * 0.1, 3),
                "content": f"[stub] pattern hint for '{user_query[:24]}'",
                "metadata": {"source_type": "stub", "timestamp": datetime.now().isoformat()},
            }
            for i in range(max(0, top_k))
        ]

    async def suggest_pattern(self, embeddings: list[float], lookback_days: int) -> dict[str, Any] | None:
        await asyncio.sleep(0)
        _ = lookback_days
        return {
            "pattern_name": "stub_pattern",
            "confidence_score": 0.5,
            "suggested_actions": [],
            "embedding_dim": len(embeddings),
        }

    async def get_memory_count(self) -> int:
        return 0


async def setup_mock_memory_fabric(params: dict[str, Any]) -> MemoryFabricStubClient:
    client = MemoryFabricStubClient(connection_params=params)
    if await client.connect_and_validate(params):
        return client
    raise RuntimeError("MemoryFabricStubClient failed validation")
