from __future__ import annotations

import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from app.application.errors import NotFoundError
from app.core.logger import get_logger
from app.core.runtime_config import get_runtime

logger = get_logger(__name__)
from app.core.secure_share_token import generate_share_token, verify_share_token
from app.domain.dto.decision_snapshot_dto import DecisionResearchSnapshotDTO
from app.infrastructure.repositories.file_decision_snapshot_repository import (
    FileDecisionSnapshotRepository,
)

INSTANCE_DIR = Path("instance/decision_snapshots")


class DecisionSnapshotService:
    """Capture and replay decision briefs for research collaboration."""

    def __init__(self, repository: FileDecisionSnapshotRepository | None = None) -> None:
        self._repo = repository or FileDecisionSnapshotRepository(INSTANCE_DIR)

    def create_snapshot(
        self,
        *,
        symbol: str,
        market: str,
        decision_brief: dict[str, Any],
        quote_snapshot: dict[str, Any] | None = None,
        sector_context: dict[str, Any] | None = None,
        label: str = "",
        notes: str = "",
        created_by: str = "anonymous",
    ) -> DecisionResearchSnapshotDTO:
        snap_id = uuid.uuid4().hex[:12]
        from flask import current_app

        secret = str(current_app.secret_key)
        share_token, share_expires_at = generate_share_token(
            snap_id,
            secret=secret,
            ttl_days=7,
        )
        dto = DecisionResearchSnapshotDTO(
            id=snap_id,
            symbol=str(symbol).strip().upper(),
            market=str(market or "CN").upper(),
            label=label or f"{symbol} {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            created_at=datetime.now(),
            created_by=created_by,
            decision_brief=decision_brief,
            quote_snapshot=quote_snapshot or (decision_brief.get("header") or {}),
            sector_context=sector_context or decision_brief.get("sector_context") or {},
            share_path=f"/decision-snapshot/{snap_id}",
            share_token=share_token,
            share_public_path=f"/share/decision/{share_token}",
            share_expires_at=share_expires_at,
            notes=notes,
        )
        result = self._repo.save(dto)
        try:
            from .decision_event_journal import DecisionEventJournal

            DecisionEventJournal(
                store_path=Path(get_runtime("DECISION_EVENT_STORE", "instance/decision_events.json"))
            ).record(
                created_by or "anonymous",
                event_type="decision_snapshot_create",
                symbol=symbol,
                market=market,
                page="stock_detail",
                component="action_bar",
                action="create_snapshot",
                detail={"snapshot_id": snap_id, "label": label},
            )
        except Exception:
            logger.warning("Suppressed exception", exc_info=True)
            pass
        return result

    def get_snapshot(self, snapshot_id: str) -> DecisionResearchSnapshotDTO:
        row = self._repo.get(snapshot_id)
        if row is None:
            raise NotFoundError("decision_snapshot_not_found")
        return row

    def get_snapshot_by_share_token(self, share_token: str) -> DecisionResearchSnapshotDTO:
        from flask import current_app


        secret = str(current_app.secret_key)
        snap_id = verify_share_token(share_token, secret=secret)
        if snap_id:
            row = self._repo.get(snap_id)
            if row is not None:
                return row
        row = self._repo.get_by_share_token(share_token)
        if row is None:
            raise NotFoundError("decision_snapshot_not_found")
        if row.share_expires_at and datetime.utcnow() > row.share_expires_at:
            raise NotFoundError("decision_snapshot_expired")
        return row

    def list_snapshots(
        self,
        *,
        symbol: str | None = None,
        limit: int = 50,
    ) -> list[DecisionResearchSnapshotDTO]:
        return self._repo.list_recent(limit=limit, symbol=symbol)
