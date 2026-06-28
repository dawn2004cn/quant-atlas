"""Vision Analyzer — multimodal LLM service for chart pattern recognition."""

from __future__ import annotations

import base64
import json
import logging
import re
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_CHART_ANALYSIS_SYSTEM_PROMPT = """你是一位资深技术分析师，拥有20年K线图形态识别经验。你的任务是分析提供的K线图，识别关键技术形态和交易信号。

请按以下结构输出分析结果（JSON格式）：

{
  "trend": "上涨/下跌/横盘",
  "trend_strength": 0.0-1.0,
  "patterns": [
    {
      "name": "形态名称（如：头肩顶、双底、上升三角形等）",
      "confidence": 0.0-1.0,
      "description": "形态描述",
      "implication": "看涨/看跌/中性",
      "target_price": "目标价（如有）",
      "stop_loss": "止损位（如有）"
    }
  ],
  "support_levels": [价格1, 价格2],
  "resistance_levels": [价格1, 价格2],
  "volume_analysis": "成交量分析",
  "key_observations": ["观察1", "观察2"],
  "overall_signal": "强烈看涨/看涨/中性/看跌/强烈看跌",
  "confidence": 0.0-1.0,
  "reasoning": "分析推理过程"
}

注意：
1. 只输出JSON，不要输出其他内容
2. 如果没有明显形态，patterns可以为空数组
3. 支撑位和阻力位基于图表中可见的关键价位
4. 所有价格使用图表中的实际价格"""


class VisionAnalyzer:
    """Multimodal LLM service for analyzing market chart images.

    Uses vision-capable LLMs (GPT-4o, Claude 3, etc.) to analyze
    chart images and identify patterns, support/resistance, and signals.
    """

    def __init__(
        self,
        *,
        model_name: str | None = None,
        llm: Any | None = None,
    ):
        self._model_name = model_name
        self._llm = llm

    def _get_llm(self) -> Any:
        if self._llm is not None:
            return self._llm
        try:
            from app.core.llm_config import get_llm
            return get_llm()
        except Exception as exc:
            logger.warning("LLM unavailable for vision analysis: %s", exc)
            return None

    def analyze_chart_image(
        self,
        *,
        image_base64: str | None = None,
        image_path: Path | str | None = None,
        symbol: str = "",
        custom_prompt: str | None = None,
    ) -> dict[str, Any]:
        """Analyze a chart image using multimodal LLM.

        Args:
            image_base64: Base64-encoded PNG image
            image_path: Path to image file (alternative to base64)
            symbol: Stock symbol for context
            custom_prompt: Optional custom analysis prompt

        Returns:
            Structured analysis result dict
        """
        llm = self._get_llm()
        if llm is None:
            return self._fallback_analysis(symbol)

        image_b64 = image_base64
        if image_b64 is None and image_path:
            try:
                with open(image_path, "rb") as f:
                    image_b64 = base64.b64encode(f.read()).decode("utf-8")
            except Exception as exc:
                logger.error("Failed to read image file: %s", exc)
                return {"status": "error", "message": f"Cannot read image: {exc}"}

        if not image_b64:
            return {"status": "error", "message": "No image provided"}

        prompt = custom_prompt or f"请分析这张{symbol + ' ' if symbol else ''}K线图的技术形态。"

        try:
            messages = [
                {"role": "system", "content": _CHART_ANALYSIS_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/png;base64,{image_b64}"},
                        },
                    ],
                },
            ]

            response = llm.invoke(messages)
            content = str(getattr(response, "content", response) or "")
            parsed = self._parse_analysis(content)
            parsed["status"] = "success"
            parsed["symbol"] = symbol
            parsed["mode"] = "llm"
            return parsed

        except Exception as exc:
            logger.error("Vision analysis failed: %s", exc)
            return {"status": "error", "message": str(exc), "symbol": symbol}

    def analyze_chart_from_data(
        self,
        stock_service: Any,
        symbol: str,
        market: str = "CN",
        *,
        days: int = 120,
        indicators: list[str] | None = None,
    ) -> dict[str, Any]:
        """Full pipeline: fetch data → render chart → analyze with vision LLM.

        Args:
            stock_service: Service with get_history() method
            symbol: Stock symbol
            market: Market code
            days: Number of trading days
            indicators: Technical indicators to overlay

        Returns:
            Combined rendering + analysis result
        """
        from app.infrastructure.vision.chart_renderer import ChartRenderer

        renderer = ChartRenderer()
        render_result = renderer.render_from_service(
            stock_service, symbol, market,
            days=days,
            indicators=indicators or ["ma5", "ma20", "ma60"],
        )

        if render_result.get("status") != "success":
            return render_result

        analysis = self.analyze_chart_image(
            image_base64=render_result.get("image_base64"),
            symbol=symbol,
        )

        return {
            "status": "success",
            "symbol": symbol,
            "chart": {
                "bar_count": render_result.get("bar_count"),
                "date_range": render_result.get("date_range"),
                "image_size_bytes": render_result.get("image_size_bytes"),
            },
            "analysis": analysis,
        }

    def _parse_analysis(self, content: str) -> dict[str, Any]:
        """Parse LLM response into structured analysis dict."""
        raw = content.strip()

        fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", raw)
        if fence:
            raw = fence.group(1).strip()

        try:
            data = json.loads(raw)
            if isinstance(data, dict):
                return self._normalize_analysis(data)
        except json.JSONDecodeError:
            logger.warning("Suppressed exception", exc_info=True)
            pass

        start = raw.find("{")
        end = raw.rfind("}")
        if start >= 0 and end > start:
            try:
                data = json.loads(raw[start:end + 1])
                if isinstance(data, dict):
                    return self._normalize_analysis(data)
            except json.JSONDecodeError:
                logger.warning("Suppressed exception", exc_info=True)
                pass

        return {
            "status": "success",
            "mode": "llm",
            "raw_response": content,
            "patterns": [],
            "overall_signal": "unknown",
            "confidence": 0.0,
        }

    @staticmethod
    def _normalize_analysis(data: dict[str, Any]) -> dict[str, Any]:
        """Normalize analysis dict with defaults."""
        patterns = data.get("patterns") or []
        normalized_patterns = []
        for p in patterns:
            if isinstance(p, dict):
                normalized_patterns.append({
                    "name": str(p.get("name", "")),
                    "confidence": float(p.get("confidence", 0)),
                    "description": str(p.get("description", "")),
                    "implication": str(p.get("implication", "neutral")),
                    "target_price": p.get("target_price"),
                    "stop_loss": p.get("stop_loss"),
                })

        return {
            "trend": str(data.get("trend", "unknown")),
            "trend_strength": float(data.get("trend_strength", 0)),
            "patterns": normalized_patterns,
            "support_levels": data.get("support_levels") or [],
            "resistance_levels": data.get("resistance_levels") or [],
            "volume_analysis": str(data.get("volume_analysis", "")),
            "key_observations": data.get("key_observations") or [],
            "overall_signal": str(data.get("overall_signal", "neutral")),
            "confidence": float(data.get("confidence", 0)),
            "reasoning": str(data.get("reasoning", "")),
        }

    @staticmethod
    def _fallback_analysis(symbol: str) -> dict[str, Any]:
        """Return a fallback analysis when LLM is unavailable."""
        return {
            "status": "success",
            "mode": "fallback",
            "symbol": symbol,
            "trend": "unknown",
            "trend_strength": 0.0,
            "patterns": [],
            "support_levels": [],
            "resistance_levels": [],
            "volume_analysis": "",
            "key_observations": ["LLM vision unavailable — analysis requires multimodal model"],
            "overall_signal": "neutral",
            "confidence": 0.0,
            "reasoning": "Vision LLM not configured",
        }


__all__ = ["VisionAnalyzer"]
