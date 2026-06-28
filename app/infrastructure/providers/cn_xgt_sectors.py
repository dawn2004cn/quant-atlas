from __future__ import annotations

"""选股通概念板块（flash-api.xuangubao.cn，与选股宝同源接口）。"""


from typing import Any

import requests
from requests import exceptions as req_exc

from app.core.logger import get_logger
from app.infrastructure.providers import DEFAULT_UA
from app.infrastructure.providers.sector_board_metrics import rise_ratio

logger = get_logger(__name__)

_RANK_URL = "https://flash-api.xuangubao.cn/api/plate/rank"
_PLATE_URL = "https://flash-api.xuangubao.cn/api/plate/plate_set"
_HEADERS = {
    "User-Agent": DEFAULT_UA,
    "Referer": "https://xuangutong.com.cn/",
    "Accept": "application/json",
}


def is_xgt_plate_code(code: str) -> bool:
    c = (code or "").strip()
    if c.lower().startswith("xgt:"):
        return True
    return c.isdigit() and len(c) >= 7


def _normalize_plate_id(sector_code: str) -> str:
    raw = (sector_code or "").strip()
    if raw.lower().startswith("xgt:"):
        return raw.split(":", 1)[1]
    return raw


def _get_json(url: str, *, params: dict[str, Any] | None = None, timeout: float = 16.0) -> dict[str, Any]:
    session = requests.Session()
    session.headers.update(_HEADERS)
    resp = session.get(url, params=params, timeout=timeout)
    resp.raise_for_status()
    payload = resp.json()
    if int(payload.get("code") or 0) != 20000:
        raise ValueError(str(payload.get("message") or "xgt_api_error"))
    return payload


def fetch_xgt_concept_boards(*, limit: int = 80) -> list[dict[str, Any]]:
    """按核心均涨幅排序的概念板块。"""
    try:
        rank_payload = _get_json(
            _RANK_URL,
            params={"field": "core_avg_pcp", "type": 1, "count": max(limit, 20)},
        )
    except (req_exc.RequestException, ValueError) as exc:
        logger.warning("xgt plate rank failed: %s", exc)
        return []

    plate_ids = [int(x) for x in (rank_payload.get("data") or [])[:limit]]
    rows: list[dict[str, Any]] = []
    for pid in plate_ids:
        try:
            detail = _get_json(_PLATE_URL, params={"id": pid}).get("data") or {}
        except (req_exc.RequestException, ValueError) as exc:
            logger.debug("xgt plate_set %s failed: %s", pid, exc)
            continue
        if not detail:
            continue
        rise = int(detail.get("rise_count") or 0)
        fall = int(detail.get("fall_count") or 0)
        core_pcp = float(detail.get("core_avg_pcp") or detail.get("avg_pcp") or 0)
        change_pct = round(core_pcp * 100, 4)
        leader_name, leader_pct = _leader_from_stocks(detail.get("stocks") or [])
        rows.append(
            {
                "sector_code": str(pid),
                "name": str(detail.get("name") or "").strip(),
                "change_pct": change_pct,
                "rise_ratio": rise_ratio(rise, fall),
                "rise_count": rise,
                "fall_count": fall,
                "leader_name": leader_name,
                "leader_change_pct": leader_pct,
                "strength": None,
                "source": "选股通概念",
                "kind": "concept",
                "provider": "xgt",
            }
        )
    return rows


def fetch_xgt_board_members(sector_code: str, *, limit: int = 80) -> list[dict[str, Any]]:
    """概念板块成分股（含核心标识）。"""
    plate_id = _normalize_plate_id(sector_code)
    if not plate_id:
        return []
    try:
        detail = _get_json(_PLATE_URL, params={"id": plate_id}).get("data") or {}
    except (req_exc.RequestException, ValueError) as exc:
        logger.warning("xgt members fetch failed plate=%s: %s", plate_id, exc)
        return []

    members: list[dict[str, Any]] = []
    for stock in (detail.get("stocks") or [])[:limit]:
        symbol_raw = str(stock.get("symbol") or "").strip()
        sym6 = "".join(ch for ch in symbol_raw if ch.isdigit())[-6:].zfill(6)
        if not sym6:
            continue
        market = "sh" if sym6.startswith(("5", "6", "9")) else "sz"
        if sym6.startswith(("4", "8")):
            market = "bj"
        members.append(
            {
                "symbol": f"{market}{sym6}",
                "code": sym6,
                "name": "",
                "change_pct": 0.0,
                "price": 0.0,
                "amount": 0.0,
                "volume": 0.0,
                "is_leader": bool(stock.get("coreleader")),
                "desc": str(stock.get("desc") or ""),
            }
        )
    return members


def _leader_from_stocks(stocks: list[dict[str, Any]]) -> tuple[str | None, float | None]:
    for stock in stocks:
        if stock.get("coreleader"):
            sym = str(stock.get("symbol") or "")
            return sym.split(".")[0][-6:], None
    if stocks:
        sym = str(stocks[0].get("symbol") or "")
        return sym.split(".")[0][-6:], None
    return None, None
