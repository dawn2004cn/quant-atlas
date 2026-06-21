from __future__ import annotations
"""Infrastructure adapter for ``QlibBinDumperPort``."""

from app.domain.ports.qlib_bin_dumper_port import QlibBinDumperPort


class QlibBinDumperPortAdapter(QlibBinDumperPort):
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
        from app.infrastructure.qlib.vendor_ms_dump_bin import DumpDataAll, DumpDataUpdate

        kw = dict(
            data_path=data_path,
            qlib_dir=qlib_dir,
            freq=freq,
            max_workers=max_workers,
            include_fields=include_fields,
        )
        if incremental:
            DumpDataUpdate(**kw).dump()
        else:
            DumpDataAll(**kw).dump()
