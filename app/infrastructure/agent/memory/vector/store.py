from __future__ import annotations

"""Vectorized Memory store for semantic agent knowledge.

Uses a local vector store to persist and retrieve agent research findings.
"""


from pathlib import Path
from typing import Any

from app.core.logger import get_logger

# Using a lightweight local vector store implementation (simulated via file-based index for now)
# In production, this would interface with chromadb or faiss
from app.infrastructure.agent.memory.persistent import PersistentMemory

logger = get_logger(__name__)

class VectorMemoryStore:
    """Semantic memory store for agent research."""

    def __init__(self, memory_dir: str = "instance/agents/memory/vector"):
        self.memory = PersistentMemory(memory_dir=Path(memory_dir))

    def add_knowledge(self, topic: str, content: str, metadata: dict[str, Any]):
        """Store knowledge semantically."""
        logger.info(f"Indexing knowledge for topic: {topic}")
        self.memory.add(
            name=topic,
            content=content,
            memory_type="vector_knowledge",
            description=metadata.get("description", "")
        )

    def retrieve_context(self, query: str, limit: int = 3) -> str:
        """Retrieve relevant knowledge based on semantic similarity."""
        relevant = self.memory.find_relevant(query, max_results=limit)
        context = "\n".join([f"## {r.title}\n{r.body}" for r in relevant])
        return context if context else "No relevant semantic memory found."
