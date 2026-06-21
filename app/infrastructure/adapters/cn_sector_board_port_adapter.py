from __future__ import annotations
"""Infrastructure adapter for ``CnSectorBoardPort``."""

from typing import Any, Literal

from app.domain.ports.cn_sector_board_port import CnSectorBoardPort, SectorKind
from app.infrastructure.providers.cn_kpl_sectors import (
    fetch_kpl_board_members,
    fetch_kpl_boards,
    is_kpl_sector_code,
)
from app.infrastructure.providers.cn_ths_sectors import (
    fetch_ths_all_boards,
    fetch_ths_board_members,
    fetch_ths_concept_boards,
    fetch_ths_csrc_boards,
    fetch_ths_industry_boards,
    fetch_ths_region_boards,
    get_ths_session,
    get_ths_session_from_settings,
    is_ths_sector_code,
    normalize_ths_board_kind,
)
from app.infrastructure.providers.cn_xgt_sectors import (
    fetch_xgt_board_members,
    fetch_xgt_concept_boards,
    is_xgt_plate_code,
)


class CnSectorBoardPortAdapter(CnSectorBoardPort):
    """Delegates to THS/KPL/XGT sector provider modules."""

    def get_ths_session(self, username: str, password: str) -> Any:
        return get_ths_session(username, password)

    def get_ths_session_from_settings(self) -> Any:
        return get_ths_session_from_settings()

    def fetch_ths_concept_boards(self, *, limit: int, session: Any = None) -> list[dict[str, Any]]:
        return fetch_ths_concept_boards(limit=limit, session=session)

    def fetch_ths_industry_boards(self, *, limit: int, session: Any = None) -> list[dict[str, Any]]:
        return fetch_ths_industry_boards(limit=limit, session=session)

    def fetch_ths_region_boards(self, *, limit: int, session: Any = None) -> list[dict[str, Any]]:
        return fetch_ths_region_boards(limit=limit, session=session)

    def fetch_ths_csrc_boards(self, *, limit: int, session: Any = None) -> list[dict[str, Any]]:
        return fetch_ths_csrc_boards(limit=limit, session=session)

    def fetch_ths_all_boards(self, *, limit_per_kind: int, session: Any = None) -> list[dict[str, Any]]:
        return fetch_ths_all_boards(limit_per_kind=limit_per_kind, session=session)

    def fetch_ths_board_members(
        self,
        code: str,
        *,
        kind: SectorKind,
        sector_name: str | None = None,
        limit: int,
        session: Any = None,
    ) -> list[dict[str, Any]]:
        return fetch_ths_board_members(
            code,
            kind=kind,
            sector_name=sector_name,
            limit=limit,
            session=session,
        )

    def fetch_kpl_boards(self, *, kind: str, limit: int) -> list[dict[str, Any]]:
        return fetch_kpl_boards(kind=kind, limit=limit)

    def fetch_kpl_board_members(self, code: str, *, limit: int) -> list[dict[str, Any]]:
        return fetch_kpl_board_members(code, limit=limit)

    def fetch_xgt_concept_boards(self, *, limit: int) -> list[dict[str, Any]]:
        return fetch_xgt_concept_boards(limit=limit)

    def fetch_xgt_board_members(self, code: str, *, limit: int) -> list[dict[str, Any]]:
        return fetch_xgt_board_members(code, limit=limit)

    def is_kpl_sector_code(self, code: str) -> bool:
        return is_kpl_sector_code(code)

    def is_ths_sector_code(self, code: str) -> bool:
        return is_ths_sector_code(code)

    def is_xgt_plate_code(self, code: str) -> bool:
        return is_xgt_plate_code(code)

    def normalize_ths_board_kind(self, kind: str | None) -> SectorKind:
        return normalize_ths_board_kind(kind)
