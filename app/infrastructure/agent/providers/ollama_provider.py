from __future__ import annotations
"""Local LLM provider using Ollama for high-performance, private inference."""


import logging
from typing import Any, Dict, List, Optional
import requests

from app.infrastructure.agent.swarm.tools_base import BaseTool
from app.infrastructure.agent.providers.chat import LLMResponse


from app.core.logger import get_logger

logger = get_logger(__name__)

class OllamaProvider:
    """Local LLM inference provider."""

    def __init__(self, model_name: str = "llama3", base_url: str = "http://localhost:11434"):
        self.model_name = model_name
        self.base_url = base_url

    def chat(self, messages: List[Dict[str, Any]], tools: Optional[List[Dict[str, Any]]] = None) -> LLMResponse:
        """Call local Ollama model."""
        payload = {
            "model": self.model_name,
            "messages": messages,
            "stream": False
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/api/chat",
                json=payload,
                timeout=300
            )
            response.raise_for_status()
            data = response.json()
            
            content = data.get("message", {}).get("content", "")
            return LLMResponse(content=content, finish_reason="stop")
            
        except Exception as e:
            logger.error(f"Ollama local inference failed: {e}")
            return LLMResponse(content=f"Inference error: {str(e)}", finish_reason="error")
