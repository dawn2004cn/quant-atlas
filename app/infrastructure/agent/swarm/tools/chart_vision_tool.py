from __future__ import annotations
"""Chart Vision Tool: Allows agents to analyze market charts visually."""


import base64
import logging
from typing import Any

from app.infrastructure.agent.swarm.tools_base import BaseTool
from app.infrastructure.agent.providers.llm import build_llm


from app.core.logger import get_logger

logger = get_logger(__name__)

class ChartVisionTool(BaseTool):
    """Analyze market charts visually using a multimodal LLM."""

    name = "chart_vision"
    description = "Analyze an image of a market chart (K-line, indicators) to identify patterns, support/resistance, or volatility visually."
    is_readonly = True
    parameters = {
        "type": "object",
        "properties": {
            "image_path": {"type": "string", "description": "Path to the chart image."},
            "question": {"type": "string", "description": "Specific question about the chart (e.g., 'Is there a head and shoulders pattern?')."},
        },
        "required": ["image_path", "question"],
    }

    def execute(self, **kwargs: Any) -> str:
        image_path = kwargs["image_path"]
        question = kwargs["question"]
        
        try:
            with open(image_path, "rb") as f:
                image_data = base64.b64encode(f.read()).decode("utf-8")
            
            # Using the existing LLM provider which is now configured for multimodal
            llm = build_llm(model_name="gpt-4o") # Example model that supports vision
            
            messages = [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": question},
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_data}"}},
                    ],
                }
            ]
            
            response = llm.invoke(messages)
            return str(response.content)
            
        except Exception as e:
            logger.error(f"Chart vision analysis failed: {e}")
            return f"Error analyzing chart: {str(e)}"
