from __future__ import annotations
"""Infrastructure adapter for ``LonghuMappingPort``."""

from typing import Any

import pandas as pd

from app.domain.ports.longhu_mapping_port import LonghuMappingPort
from app.infrastructure.mappers.longhu_mapper import LonghuMapper


class LonghuMappingPortAdapter(LonghuMappingPort):
    def map_dataframe_to_entries(self, df: pd.DataFrame) -> list[Any]:
        return LonghuMapper.map_dataframe_to_entries(df)
