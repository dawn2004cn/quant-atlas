from __future__ import annotations

"""Port for mapping raw longhu DataFrames to domain entries."""

from typing import Any, Protocol

import pandas as pd


class LonghuMappingPort(Protocol):
    def map_dataframe_to_entries(self, df: pd.DataFrame) -> list[Any]:
        ...
