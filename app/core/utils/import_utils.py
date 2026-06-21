from __future__ import annotations
"""Smart import service for stock code parsing."""


import io
import logging
import re
from typing import Any

import pandas as pd

from ...core.logger import get_logger
from ...infrastructure.mappers.symbol_normalizer import SymbolNormalizer


logger = get_logger(__name__)

_CODE_ALIASES = frozenset({"code", "股票代码", "代码", "stock_code", "symbol"})
_NAME_ALIASES = frozenset({"name", "股票名称", "名称", "stock_name"})


class ImportService:
    """Parse stock codes from various sources."""

    def parse_text(self, text: str) -> list[str]:
        """Extract possible stock codes from plain text."""
        if not text:
            return []

        codes = re.findall(r"\b\d{6}\b|\b[A-Z]{2,5}\b", text)

        normalized = []
        for c in codes:
            try:
                norm = SymbolNormalizer.normalize_code(c)
                if norm not in normalized:
                    normalized.append(norm)
            except Exception:
                continue
        return normalized

    def parse_csv(self, data: bytes) -> list[str]:
        """Parse stock codes from CSV bytes."""
        try:
            df = pd.read_csv(io.BytesIO(data))
            return self._parse_dataframe(df)
        except Exception as e:
            logger.error(f"CSV parsing failed: {e}")
            return []

    def _parse_dataframe(self, df: pd.DataFrame) -> list[str]:
        """Identify code column and extract codes."""
        code_col = None
        cols = [str(c).strip().lower() for c in df.columns]

        for i, c in enumerate(cols):
            if c in _CODE_ALIASES:
                code_col = df.columns[i]
                break

        if code_col is None:
            code_col = df.columns[0]

        codes = df[code_col].astype(str).tolist()
        result = []
        for c in codes:
            c = c.strip()
            if not c:
                continue
            try:
                norm = SymbolNormalizer.normalize_code(c)
                if norm not in result:
                    result.append(norm)
            except Exception:
                continue
        return result

    async def extract_from_image(self, image_bytes: bytes, llm_service: Any) -> list[str]:
        """Extract stock codes from image using Vision LLM."""
        logger.info("Image extraction triggered (stub)")
        return []