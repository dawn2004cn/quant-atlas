from __future__ import annotations
"""Port for CN sector board data (THS / KPL / XGT)."""

from typing import Any, Literal, Protocol

SectorKind = Literal["concept", "industry", "region", "csrc"]


class CnSectorBoardPort(Protocol):
    """Application-facing sector board fetchers."""

    def get_ths_session(self, username: str, password: str) -> Any:
        ...

    def get_ths_session_from_settings(self) -> Any:
        """Return authenticated session from app settings, or anonymous session."""
        ...

    def fetch_ths_concept_boards(self, *, limit: int, session: Any = None) -> list[dict[str, Any]]:
        ...

    def fetch_ths_industry_boards(self, *, limit: int, session: Any = None) -> list[dict[str, Any]]:
        ...

    def fetch_ths_region_boards(self, *, limit: int, session: Any = None) -> list[dict[str, Any]]:
        ...

    def fetch_ths_csrc_boards(self, *, limit: int, session: Any = None) -> list[dict[str, Any]]:
        ...

    def fetch_ths_all_boards(self, *, limit_per_kind: int, session: Any = None) -> list[dict[str, Any]]:
        ...

    def fetch_ths_board_members(
        self,
        code: str,
        *,
        kind: SectorKind,
        sector_name: str | None = None,
        limit: int,
        session: Any = None,
    ) -> list[dict[str, Any]]:
        ...

    def fetch_kpl_boards(self, *, kind: str, limit: int) -> list[dict[str, Any]]:
        ...

    def fetch_kpl_board_members(self, code: str, *, limit: int) -> list[dict[str, Any]]:
        ...

    def fetch_xgt_concept_boards(self, *, limit: int) -> list[dict[str, Any]]:
        ...

    def fetch_xgt_board_members(self, code: str, *, limit: int) -> list[dict[str, Any]]:
        ...

    def is_kpl_sector_code(self, code: str) -> bool:
        ...

    def is_ths_sector_code(self, code: str) -> bool:
        ...

    def is_xgt_plate_code(self, code: str) -> bool:
        ...

    def normalize_ths_board_kind(self, kind: str | None) -> SectorKind:
        ...
