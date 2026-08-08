"""Shadow Account page — trade journal upload analysis for SPA."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

from werkzeug.datastructures import FileStorage

from app.core.logger import get_logger
from app.infrastructure.agent.shadow_account.extractor import extract_shadow_profile
from app.infrastructure.agent.swarm.tools.trade_journal_parsers import parse_file, records_to_dataframe
from app.infrastructure.agent.swarm.tools.trade_journal_tool import pair_trades_fifo

logger = get_logger(__name__)

_last_result_by_user: dict[str, dict[str, Any]] = {}


def get_status(user_key: str) -> dict[str, Any] | None:
    """Return the user's last analysis snapshot, if any."""
    return _last_result_by_user.get(user_key)


def analyze_upload(user_key: str, upload: FileStorage) -> dict[str, Any]:
    """Parse an uploaded journal file and return summary metrics."""
    if upload is None or not upload.filename:
        raise ValueError("file_required")

    suffix = Path(upload.filename).suffix.lower() or ".csv"
    if suffix not in {".csv", ".xlsx", ".xls"}:
        raise ValueError("unsupported_file_type")

    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        upload.save(tmp.name)
        journal_path = Path(tmp.name)

    try:
        result = _analyze_journal(journal_path)
        _last_result_by_user[user_key] = result
        return result
    finally:
        journal_path.unlink(missing_ok=True)


def _analyze_journal(journal_path: Path) -> dict[str, Any]:
    _fmt, records = parse_file(journal_path)
    if not records:
        raise ValueError("no_trade_records")

    trades_df = records_to_dataframe(records)
    roundtrips = pair_trades_fifo(trades_df)
    if not roundtrips:
        raise ValueError("no_roundtrips")

    total = len(roundtrips)
    wins = sum(1 for rt in roundtrips if rt["pnl"] > 0)
    win_rate = wins / total if total else 0.0
    total_return = sum(float(rt.get("pnl_pct") or 0.0) for rt in roundtrips)

    summary = f"共解析 {total} 笔完整交易，胜率 {win_rate:.1%}，累计收益率 {total_return:.2%}"

    try:
        profile = extract_shadow_profile(journal_path)
        if profile.profile_text:
            summary = profile.profile_text
    except ValueError as exc:
        logger.info("shadow profile extraction skipped for %s: %s", journal_path.name, exc)

    return {
        "total_trades": total,
        "win_rate": round(win_rate, 4),
        "total_return": round(total_return, 4),
        "summary": summary,
    }
