from __future__ import annotations

"""板块榜单通用指标：涨股比、龙头等（domain 纯函数）。"""

from typing import Any


def rise_ratio(up_count: int | float | None, down_count: int | float | None) -> float | None:
    """上涨家数 / (上涨 + 下跌)，无有效样本时返回 None。"""
    up = int(up_count or 0)
    down = int(down_count or 0)
    total = up + down
    if total <= 0:
        return None
    return round(up / total, 4)


def leader_from_members(members: list[dict[str, Any]]) -> tuple[str | None, float | None]:
    """从成分股列表取涨幅最高者作为龙头。"""
    best_name: str | None = None
    best_pct: float | None = None
    for row in members:
        pct = row.get("change_pct")
        if pct is None:
            continue
        try:
            val = float(pct)
        except (TypeError, ValueError):
            continue
        if best_pct is None or val > best_pct:
            best_pct = val
            best_name = str(row.get("name") or "").strip() or None
    return best_name, best_pct


def aggregate_member_stats(members: list[dict[str, Any]]) -> dict[str, Any]:
    """根据成分股涨跌幅汇总板块涨股比、均涨幅、龙头。"""
    pcts: list[float] = []
    up = 0
    down = 0
    flat = 0
    for row in members:
        try:
            pct = float(row.get("change_pct") or 0)
        except (TypeError, ValueError):
            continue
        pcts.append(pct)
        if pct > 0:
            up += 1
        elif pct < 0:
            down += 1
        else:
            flat += 1
    rr = rise_ratio(up, down)
    avg_chg = round(sum(pcts) / len(pcts), 4) if pcts else 0.0
    leader_name, leader_pct = leader_from_members(members)
    return {
        "change_pct": avg_chg,
        "rise_ratio": rr,
        "rise_count": up,
        "fall_count": down,
        "flat_count": flat,
        "leader_name": leader_name,
        "leader_change_pct": leader_pct,
    }
