from __future__ import annotations
"""Port for dumping qlib_export CSV into qlib_bin."""

from typing import Protocol


class QlibBinDumperPort(Protocol):
    def dump(
        self,
        *,
        data_path: str,
        qlib_dir: str,
        freq: str,
        max_workers: int,
        include_fields: str,
        incremental: bool,
    ) -> None:
        ...
