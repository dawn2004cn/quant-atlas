from __future__ import annotations
"""Longhu data mappers for transformation."""

import pandas as pd
from app.domain.shared.eastmoney_parser import EastmoneyParser
from app.domain.shared.symbol_normalizer import SymbolNormalizer
from app.core.utils.datetime_utils import norm_date
from app.domain.dto.market_data_dto import LonghuEntry
from app.core.utils.pandas_utils import json_safe

class LonghuMapper:
    """Maps Raw DataFrames to Domain DTOs."""

    @staticmethod
    def map_dataframe_to_entries(df: pd.DataFrame) -> list[LonghuEntry]:
        parser = EastmoneyParser()
        code_c = parser.find_col(df, "代码") or parser.find_col(df, "股票", "代码")
        name_c = parser.find_col(df, "名称") or parser.find_col(df, "简称")
        date_c = parser.find_col(df, "日期") or parser.find_col(df, "上榜", "日期")
        reason_c = parser.find_col(df, "上榜", "原因") or parser.find_col(df, "原因")

        entries = []
        for _, r in df.iterrows():
            raw_row = {str(k): json_safe(v) for k, v in r.items()}

            code_raw = str(r.get(code_c) if code_c else "").strip()
            if not code_raw:
                code_raw = parser.find_value_by_regex(list(raw_row.values()), r"\b\d{6}\b")
            code = SymbolNormalizer.normalize_code(code_raw)
            if len(code) != 6: continue

            date_raw = str(r.get(date_c) if date_c else "").strip()
            if not date_raw:
                date_raw = parser.find_value_by_regex(list(raw_row.values()), r"\b\d{4}-\d{2}-\d{2}\b")
            td = norm_date(date_raw)
            if len(td) != 10: continue

            name = str(r.get(name_c) or "")[:64]
            reason = str(r.get(reason_c) or "")[:512]

            entries.append(
                LonghuEntry(trade_date=td, code=code, name=name, reason=reason, raw=raw_row)
            )
        return entries
