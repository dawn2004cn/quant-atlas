"""Fill empty workbench panels with labeled demo rows so the SPA is never blank."""

from __future__ import annotations

from typing import Any

_DEMO_WATCHLIST: dict[str, list[dict[str, Any]]] = {
    "CN": [
        {"code": "600519", "name": "贵州茅台", "price": 1688.0, "change_pct": 1.24, "health_score": 72},
        {"code": "000858", "name": "五粮液", "price": 128.6, "change_pct": -0.62, "health_score": 48},
        {"code": "601318", "name": "中国平安", "price": 48.2, "change_pct": 0.85, "health_score": 64},
        {"code": "000333", "name": "美的集团", "price": 72.1, "change_pct": 0.31, "health_score": 58},
        {"code": "600036", "name": "招商银行", "price": 36.8, "change_pct": -0.22, "health_score": 51},
    ],
    "HK": [
        {"code": "00700", "name": "腾讯控股", "price": 380.0, "change_pct": 0.92, "health_score": 66},
        {"code": "09988", "name": "阿里巴巴", "price": 82.4, "change_pct": -0.41, "health_score": 49},
        {"code": "00941", "name": "中国移动", "price": 68.5, "change_pct": 0.18, "health_score": 55},
    ],
    "US": [
        {"code": "AAPL", "name": "Apple", "price": 228.4, "change_pct": 0.55, "health_score": 61},
        {"code": "MSFT", "name": "Microsoft", "price": 415.2, "change_pct": 0.22, "health_score": 59},
        {"code": "NVDA", "name": "NVIDIA", "price": 118.6, "change_pct": 1.80, "health_score": 74},
    ],
}

_DEMO_MACRO: dict[str, list[dict[str, Any]]] = {
    "CN": [
        {"label": "上证指数", "code": "SH000001", "price": 3278.4, "change_pct": 0.46},
        {"label": "深证成指", "code": "SZ399001", "price": 10412.0, "change_pct": 0.31},
        {"label": "沪深300", "code": "SH000300", "price": 3890.2, "change_pct": 0.52},
        {"label": "创业板指", "code": "SZ399006", "price": 2118.7, "change_pct": -0.18},
    ],
    "HK": [
        {"label": "恒生指数", "code": "HSI", "price": 17820.0, "change_pct": 0.38},
        {"label": "国企指数", "code": "HSCEI", "price": 6120.0, "change_pct": 0.21},
    ],
    "US": [
        {"label": "S&P 500", "code": "SPX", "price": 5480.0, "change_pct": 0.29},
        {"label": "Nasdaq", "code": "IXIC", "price": 17640.0, "change_pct": 0.41},
    ],
}

_DEMO_HEADLINES = [
    {
        "title": "权重股带动指数修复，成交额回到季节中枢",
        "source": "演示",
        "summary": "展示用样本，非实时资讯",
    },
    {
        "title": "机构调研聚焦消费与金融，关注回撤后的赔率",
        "source": "演示",
        "summary": "展示用样本，非实时资讯",
    },
    {
        "title": "北向资金波动收敛，短线情绪转为中性偏多",
        "source": "演示",
        "summary": "展示用样本，非实时资讯",
    },
]

_DEMO_RECS = [
    {"code": "600519", "name": "贵州茅台", "reason": "演示：高ROE + 回撤后赔率", "score": 82},
    {"code": "601318", "name": "中国平安", "reason": "演示：估值与股息平衡", "score": 74},
    {"code": "000333", "name": "美的集团", "reason": "演示：盈利质量稳定", "score": 71},
]

_DEMO_BREADTH = {"up": 1842, "down": 1260, "flat": 418, "total": 3520}


def apply_display_fallback(payload: dict[str, Any], market: str) -> dict[str, Any]:
    """Ensure key dashboard arrays are non-empty; mark injected parts as demo."""
    demo_parts: list[str] = []
    key = (market or "CN").upper()
    if key not in _DEMO_WATCHLIST:
        key = "CN"

    watchlist = payload.get("watchlist_health") if isinstance(payload.get("watchlist_health"), dict) else {}
    items = list(watchlist.get("items") or []) if isinstance(watchlist, dict) else []
    if not items:
        payload["watchlist_health"] = {
            "items": [dict(row) for row in _DEMO_WATCHLIST[key]],
            "summary": "演示自选（暂无实时持仓）",
            "demo": True,
        }
        demo_parts.append("watchlist")

    macros = payload.get("macro_indices") or []
    if not macros:
        payload["macro_indices"] = [dict(row) for row in _DEMO_MACRO[key]]
        demo_parts.append("macro")

    panorama = payload.get("market_panorama") if isinstance(payload.get("market_panorama"), dict) else {}
    up = int(panorama.get("up") or 0) if isinstance(panorama, dict) else 0
    down = int(panorama.get("down") or 0) if isinstance(panorama, dict) else 0
    flat = int(panorama.get("flat") or 0) if isinstance(panorama, dict) else 0
    if up + down + flat <= 0:
        payload["market_panorama"] = dict(_DEMO_BREADTH)
        sentiment = payload.get("market_sentiment") if isinstance(payload.get("market_sentiment"), dict) else {}
        merged = dict(sentiment) if isinstance(sentiment, dict) else {}
        merged.setdefault("score", 56)
        merged.setdefault("level", "中性偏多")
        merged.setdefault("description", "演示市场宽度（行情源未就绪）")
        merged.setdefault("emoji", "📊")
        merged["stats"] = {
            "gainers": _DEMO_BREADTH["up"],
            "losers": _DEMO_BREADTH["down"],
            "neutral": _DEMO_BREADTH["flat"],
            "total": _DEMO_BREADTH["total"],
        }
        payload["market_sentiment"] = merged
        demo_parts.append("breadth")

    headlines = payload.get("headlines") or []
    if not headlines:
        payload["headlines"] = [dict(row) for row in _DEMO_HEADLINES]
        demo_parts.append("headlines")

    rec = payload.get("recommendations_preview") if isinstance(payload.get("recommendations_preview"), dict) else {}
    rec_items = list(rec.get("items") or []) if isinstance(rec, dict) else []
    if not rec_items:
        note = (rec.get("message") if isinstance(rec, dict) else None) or "演示推荐"
        payload["recommendations_preview"] = {
            "items": [dict(row) for row in _DEMO_RECS],
            "note": note,
            "demo": True,
        }
        demo_parts.append("recommendations")

    if demo_parts and (items or up + down + flat > 0):
        payload["data_mode"] = "mixed"
    elif demo_parts:
        payload["data_mode"] = "demo"
    else:
        payload["data_mode"] = "live"
    payload["demo_parts"] = demo_parts
    return payload
