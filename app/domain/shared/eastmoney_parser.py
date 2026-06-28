from __future__ import annotations

"""Parser for Eastmoney-style data (Dataframes and JSONP) — domain 纯逻辑."""

import json
import logging
import re
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)
class EastmoneyParser:
    """Utility class for parsing Eastmoney web/API responses."""

    @staticmethod
    def find_col(df: pd.DataFrame, *needles: str) -> str | None:
        for c in df.columns:
            s = str(c)
            if all(n in s for n in needles):
                return c
        for c in df.columns:
            s = str(c)
            if any(n in s for n in needles):
                return c
        return None

    @staticmethod
    def find_value_by_regex(values: list[Any], pattern: str) -> str:
        rx = re.compile(pattern)
        for v in values:
            s = str(v or "").strip()
            if s and rx.search(s):
                return s
        return ""

    @staticmethod
    def pick_first_str(row: dict[str, Any], *, key_needles: tuple[str, ...], value_regex: str | None = None) -> str:
        for k, v in row.items():
            ks = str(k)
            if any(n in ks for n in key_needles):
                s = str(v or "").strip()
                if s:
                    return s
        if value_regex is not None:
            return EastmoneyParser.find_value_by_regex(list(row.values()), value_regex)
        return ""

    @staticmethod
    def parse_json_or_jsonp(text: str) -> dict[str, Any]:
        raw = (text or "").strip()
        if not raw:
            return {}
        try:
            return json.loads(raw)
        except json.JSONDecodeError as e:
            logger.warning("eastmoney_parser.py.parse_json_or_jsonp: %s", e)
        m = re.search(r"\((\{[\s\S]+\})\)\s*;?\s*$", raw)
        if m:
            try:
                return json.loads(m.group(1))
            except json.JSONDecodeError:
                return {}
        return {}
