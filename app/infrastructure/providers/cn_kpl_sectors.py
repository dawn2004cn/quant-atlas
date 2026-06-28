from __future__ import annotations

"""开盘啦板块：概念 / 地区 / 行业（apphq.longhuvip.com）。"""


from datetime import date
from typing import Any, Literal

import requests
from requests import exceptions as req_exc

from app.core.logger import get_logger
from app.infrastructure.providers.sector_board_metrics import rise_ratio

logger = get_logger(__name__)

KplBoardKind = Literal["concept", "region", "industry"]

_LIVE_URL = "https://apphq.longhuvip.com/w1/api/index.php"
_HIST_URL = "https://apphis.longhuvip.com/w1/api/index.php"
_HEADERS = {
    "User-Agent": "lhb/5.17.9 (com.kaipanla.www; build:0; iOS 16.6.0) Alamofire/4.9.1",
    "Content-Type": "application/x-www-form-urlencoded; charset=utf-8",
    "Accept": "*/*",
}
_ZSTYPE: dict[KplBoardKind, str] = {
    "concept": "7",
    "region": "5",
    "industry": "4",
}
_SOURCE_LABEL: dict[KplBoardKind, str] = {
    "concept": "开盘啦概念",
    "region": "开盘啦地区",
    "industry": "开盘啦行业",
}


def is_kpl_sector_code(code: str) -> bool:
    c = (code or "").strip()
    if c.startswith("kpl:"):
        return True
    return len(c) == 6 and c.isdigit() and c.startswith(("801", "881", "885"))


def _normalize_plate_id(sector_code: str) -> str:
    raw = (sector_code or "").strip()
    if raw.lower().startswith("kpl:"):
        return raw.split(":", 1)[1]
    return raw


def _post(url: str, payload: dict[str, str], *, timeout: float = 14.0) -> dict[str, Any]:
    session = requests.Session()
    session.headers.update(_HEADERS)
    resp = session.post(url, data=payload, timeout=timeout)
    resp.raise_for_status()
    return resp.json()


def fetch_kpl_boards(*, kind: KplBoardKind = "concept", limit: int = 80) -> list[dict[str, Any]]:
    """涨幅/强度榜；``kind``：concept / region / industry。"""
    today = date.today().strftime("%Y-%m-%d")
    payload = {
        "Date": today,
        "Index": "0",
        "Order": "1",
        "PhoneOSNew": "2",
        "Type": "1",
        "VerSion": "5.17.0.9",
        "ZSType": _ZSTYPE[kind],
        "a": "RealRankingInfo",
        "apiv": "w38",
        "c": "ZhiShuRanking",
        "st": str(max(limit, 20)),
    }
    try:
        data = _post(_LIVE_URL, payload)
    except (req_exc.RequestException, ValueError) as exc:
        logger.warning("kpl board fetch failed kind=%s: %s", kind, exc)
        return []

    rows: list[dict[str, Any]] = []
    for item in (data.get("list") or [])[:limit]:
        if not isinstance(item, (list, tuple)) or len(item) < 4:
            continue
        code = str(item[0] or "").strip()
        name = str(item[1] or "").strip()
        if not code or not name:
            continue
        strength = _to_float(item[2])
        change_pct = _to_float(item[3])
        up_metric = _to_float(item[15]) if len(item) > 15 else None
        down_metric = _to_float(item[16]) if len(item) > 16 else None
        rr = None
        if up_metric is not None and down_metric is not None and (up_metric + down_metric) > 0:
            rr = round(up_metric / (up_metric + down_metric), 4)
        rows.append(
            {
                "sector_code": code,
                "name": name,
                "change_pct": change_pct,
                "strength": strength,
                "rise_ratio": rr,
                "leader_name": None,
                "leader_change_pct": None,
                "source": _SOURCE_LABEL[kind],
                "kind": "concept" if kind == "concept" else ("region" if kind == "region" else "industry"),
                "provider": "kpl",
            }
        )
    return rows


def fetch_kpl_board_members(
    sector_code: str,
    *,
    limit: int = 80,
) -> list[dict[str, Any]]:
    """板块成分股（交易时段有数据；非交易可能为空）。"""
    plate_id = _normalize_plate_id(sector_code)
    if not plate_id:
        return []

    today = date.today().strftime("%Y-%m-%d")
    payload = {
        "PlateID": plate_id,
        "Date": today,
        "Index": "0",
        "Order": "1",
        "PhoneOSNew": "2",
        "Type": "6",
        "VerSion": "5.17.0.9",
        "ZSType": "7",
        "a": "ZhiShuStockList",
        "apiv": "w38",
        "c": "ZhiShuRanking",
        "st": str(max(limit, 20)),
    }
    try:
        data = _post(_LIVE_URL, payload)
    except (req_exc.RequestException, ValueError) as exc:
        logger.warning("kpl members fetch failed plate=%s: %s", plate_id, exc)
        return []

    members: list[dict[str, Any]] = []
    for item in (data.get("list") or [])[:limit]:
        if not isinstance(item, (list, tuple)) or len(item) < 7:
            continue
        sym6 = str(item[0] or "").strip()[-6:].zfill(6)
        name = str(item[1] or "").strip()
        change_pct = _to_float(item[6]) if len(item) > 6 else 0.0
        price = _to_float(item[5]) if len(item) > 5 else 0.0
        amount = _to_float(item[7]) if len(item) > 7 else 0.0
        market = "sh" if sym6.startswith(("5", "6", "9")) else "sz"
        if sym6.startswith(("4", "8")):
            market = "bj"
        is_leader = False
        if len(item) > 24:
            try:
                is_leader = int(item[24] or 0) > 0
            except (TypeError, ValueError):
                is_leader = False
        members.append(
            {
                "symbol": f"{market}{sym6}",
                "code": sym6,
                "name": name,
                "change_pct": change_pct,
                "price": price,
                "amount": amount,
                "volume": 0.0,
                "is_leader": is_leader,
            }
        )
    members.sort(key=lambda x: x["change_pct"], reverse=True)
    if members and not any(m.get("is_leader") for m in members):
        members[0]["is_leader"] = True
    return members


def enrich_kpl_board_leader(row: dict[str, Any], members: list[dict[str, Any]]) -> dict[str, Any]:
    """用成分股补全龙头信息。"""
    out = dict(row)
    leader = next((m for m in members if m.get("is_leader")), None)
    if leader is None and members:
        leader = members[0]
    if leader:
        out["leader_name"] = leader.get("name")
        out["leader_change_pct"] = leader.get("change_pct")
    up = sum(1 for m in members if float(m.get("change_pct") or 0) > 0)
    down = sum(1 for m in members if float(m.get("change_pct") or 0) < 0)
    rr = rise_ratio(up, down)
    if rr is not None:
        out["rise_ratio"] = rr
    return out


def _to_float(value: Any) -> float:
    try:
        if value is None or value == "-":
            return 0.0
        return float(value)
    except (TypeError, ValueError):
        return 0.0
