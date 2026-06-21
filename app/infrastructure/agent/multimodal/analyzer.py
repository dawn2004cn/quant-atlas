from __future__ import annotations
"""Multimodal Market Intelligence Engine."""

import logging
from typing import Any, Dict
from pathlib import Path
import base64

from app.infrastructure.agent.providers.llm import build_llm


from app.core.logger import get_logger

logger = get_logger(__name__)

class MultimodalAnalyzer:
    """Analyzes charts and documents visually."""

    def __init__(self, model_name: str = "gpt-4o"):
        self.llm = build_llm(model_name=model_name)

    def analyze_chart(self, image_path: Path, prompt: str) -> Dict[str, Any]:
        """Process an image file to extract market intelligence."""
        logger.info(f"Analyzing chart: {image_path}")
        
        try:
            with open(image_path, "rb") as f:
                image_base64 = base64.b64encode(f.read()).decode('utf-8')
                
            payload = [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_base64}"}}
            ]
            
            response = self.llm.invoke([{"role": "user", "content": payload}])
            return {"analysis": str(response.content), "status": "success"}
            
        except Exception as e:
            logger.error(f"Vision analysis failed: {e}")
            return {"status": "error", "message": str(e)}
