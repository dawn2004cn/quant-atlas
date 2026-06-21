from __future__ import annotations
"""Build supporting_evidence with factor values and 250-day percentiles."""

from typing import Any

from app.core.logger import get_logger

logger = get_logger(__name__)

_WINDOW_DAYS = 250


def _percentile_rank(series: list[float], value: float) -> float | None:
    clean = [v for v in series if v == v]
    if len(clean) < 20 or value != value:
        return None
    below = sum(1 for v in clean if v <= value)
    return round(below / len(clean) * 100, 1)


def _rsi(closes: list[float], period: int = 14) -> float | None:
    if len(closes) < period + 1:
        return None
    gains: list[float] = []
    losses: list[float] = []
    for i in range(-period, 0):
        delta = closes[i] - closes[i - 1]
        if delta >= 0:
            gains.append(delta)
            losses.append(0.0)
        else:
            gains.append(0.0)
            losses.append(-delta)
    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period
    if avg_loss <= 0:
        return 100.0
    rs = avg_gain / avg_loss
    return round(100 - (100 / (1 + rs)), 2)


def _normalize_symbol_code(symbol: str) -> str:
    text = str(symbol or "").strip().upper()
    for suffix in (".SH", ".SZ", ".HK"):
        if text.endswith(suffix):
            text = text[: -len(suffix)]
    return text[:6] if text.isdigit() else text


def _build_report_citations(symbol: str, yanbao_items: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    code = _normalize_symbol_code(symbol)
    if not code or not yanbao_items:
        return []
    matched: list[dict[str, Any]] = []
    for row in yanbao_items:
        sc = str(row.get("stock_code") or "").strip()
        sc6 = _normalize_symbol_code(sc) if sc else ""
        if sc6 != code and code not in sc and sc6 not in code:
            continue
        title = str(row.get("title") or "").strip()
        if not title:
            continue
        raw = row.get("raw") if isinstance(row.get("raw"), dict) else {}
        excerpt = str(raw.get("abstract") or raw.get("summary") or title)[:280]
        matched.append(
            {
                "id": f"yanbao_{row.get('id', len(matched))}",
                "title": title,
                "org_name": str(row.get("org_name") or ""),
                "pub_date": str(row.get("pub_date") or ""),
                "excerpt": excerpt,
                "report_url": str(row.get("report_url") or ""),
                "source": "yanbao_items",
                "trace_ref": {
                    "anchor": "yanbao_citation",
                    "section_id": "supporting-evidence",
                    "field": "研报原文",
                    "label": title[:60],
                    "symbol": symbol,
                    "market": "CN",
                },
            }
        )
    return matched[:3]


class EvidenceTraceabilityService:
    """Attach traceable factor evidence to decision briefs."""

    def build_supporting_evidence(
        self,
        *,
        symbol: str,
        market: str,
        quote: dict[str, Any],
        history: list[dict[str, Any]],
        indicators: dict[str, Any] | None = None,
        yanbao_items: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        closes = [
            float(r.get("close") or r.get("Close") or 0)
            for r in history
            if float(r.get("close") or r.get("Close") or 0) > 0
        ]
        volumes = [
            float(r.get("volume") or r.get("Volume") or 0)
            for r in history
            if float(r.get("volume") or r.get("Volume") or 0) > 0
        ]
        price = float(quote.get("price") or (closes[-1] if closes else 0) or 0)
        change_pct = float(quote.get("change_pct") or 0)

        factors: list[dict[str, Any]] = []

        if len(volumes) >= 25:
            vol_today = volumes[-1]
            vol_avg20 = sum(volumes[-21:-1]) / 20
            vol_ratio = round(vol_today / vol_avg20, 2) if vol_avg20 > 0 else 0.0
            vol_series = [
                volumes[i] / (sum(volumes[max(0, i - 20) : i]) / min(20, i) or 1)
                for i in range(21, len(volumes))
            ]
            factors.append(
                {
                    "id": "volume_breakout",
                    "name": "成交量突破",
                    "value": vol_ratio,
                    "unit": "x20日均",
                    "percentile_250d": _percentile_rank(vol_series[-_WINDOW_DAYS :], vol_ratio),
                    "interpretation": (
                        "量能显著放大，资金关注度提升"
                        if vol_ratio >= 1.5
                        else "量能中性，需结合价格确认"
                    ),
                    "supports_stance": "bullish" if vol_ratio >= 1.8 and change_pct > 0 else "neutral",
                    "trace_ref": {
                        "anchor": "volume_breakout",
                        "section_id": "supporting-evidence",
                        "field": "成交量突破",
                        "label": "量能显著放大" if vol_ratio >= 1.5 else "量能中性",
                        "symbol": symbol,
                        "market": market,
                    },
                }
            )

        if len(closes) >= 30:
            rsi_val = _rsi(closes)
            if rsi_val is not None:
                rsi_hist = []
                for i in range(15, len(closes)):
                    seg = closes[: i + 1]
                    r = _rsi(seg)
                    if r is not None:
                        rsi_hist.append(r)
                factors.append(
                    {
                        "id": "rsi_14",
                        "name": "RSI(14)",
                        "value": rsi_val,
                        "unit": "index",
                        "percentile_250d": _percentile_rank(rsi_hist[-_WINDOW_DAYS :], rsi_val),
                        "interpretation": (
                            "超卖区，反弹概率上升"
                            if rsi_val < 35
                            else "超买区，追涨需谨慎"
                            if rsi_val > 70
                            else "动量中性"
                        ),
                        "supports_stance": "bullish" if rsi_val < 35 else "bearish" if rsi_val > 70 else "neutral",
                        "trace_ref": {
                            "anchor": "rsi_14",
                            "section_id": "supporting-evidence",
                            "field": "RSI(14)",
                            "label": "超卖区" if rsi_val < 35 else "超买区" if rsi_val > 70 else "动量中性",
                            "symbol": symbol,
                            "market": market,
                        },
                    }
                )

        if len(closes) >= 20:
            ma20 = sum(closes[-20:]) / 20
            dist_pct = round((price - ma20) / ma20 * 100, 2) if ma20 > 0 else 0.0
            dist_series = [
                (closes[i] - sum(closes[max(0, i - 19) : i + 1]) / min(20, i + 1))
                / (sum(closes[max(0, i - 19) : i + 1]) / min(20, i + 1) or 1)
                * 100
                for i in range(19, len(closes))
            ]
            factors.append(
                {
                    "id": "ma20_distance",
                    "name": "相对20日均线",
                    "value": dist_pct,
                    "unit": "%",
                    "percentile_250d": _percentile_rank(dist_series[-_WINDOW_DAYS :], dist_pct),
                    "interpretation": (
                        "价格运行于均线之上，趋势偏多"
                        if dist_pct > 2
                        else "价格弱于均线，谨慎看多"
                        if dist_pct < -2
                        else "贴近均线震荡"
                    ),
                    "supports_stance": "bullish" if dist_pct > 2 else "bearish" if dist_pct < -2 else "neutral",
                    "trace_ref": {
                        "anchor": "ma20_distance",
                        "section_id": "supporting-evidence",
                        "field": "相对20日均线",
                        "label": "趋势偏多" if dist_pct > 2 else "谨慎看多" if dist_pct < -2 else "贴近均线震荡",
                        "symbol": symbol,
                        "market": market,
                    },
                }
            )

        ind = indicators or {}
        if ind.get("macd") is not None or ind.get("macd_signal") is not None:
            macd_sig = float(ind.get("macd_signal") or ind.get("macd") or 0)
            factors.append(
                {
                    "id": "macd_signal",
                    "name": "MACD 信号",
                    "value": macd_sig,
                    "unit": "indicator",
                    "percentile_250d": None,
                    "interpretation": "平台指标快照，可与 K 线 MACD 交叉对照",
                    "supports_stance": "bullish" if macd_sig > 0 else "bearish" if macd_sig < 0 else "neutral",
                    "trace_ref": {
                        "anchor": "macd_signal",
                        "section_id": "supporting-evidence",
                        "field": "MACD 信号",
                        "label": "MACD 指标快照",
                        "symbol": symbol,
                        "market": market,
                    },
                }
            )

        factors = factors[:3]
        report_citations = _build_report_citations(symbol, yanbao_items)
        if report_citations:
            factors.append(
                {
                    "id": "yanbao_consensus",
                    "name": "研报覆盖",
                    "value": len(report_citations),
                    "unit": "篇",
                    "percentile_250d": None,
                    "interpretation": "近期有相关研报条目，详见下方原文摘要",
                    "supports_stance": "neutral",
                    "report_refs": [c.get("id") for c in report_citations],
                    "trace_ref": {
                        "anchor": "yanbao_consensus",
                        "section_id": "supporting-evidence",
                        "field": "研报覆盖",
                        "label": f"{len(report_citations)} 篇近期研报",
                        "symbol": symbol,
                        "market": market,
                    },
                }
            )
            factors = factors[:4]

        bullish = sum(1 for f in factors if f.get("supports_stance") == "bullish")
        bearish = sum(1 for f in factors if f.get("supports_stance") == "bearish")
        if bullish > bearish:
            stance = "bullish"
            verdict = "偏多"
        elif bearish > bullish:
            stance = "bearish"
            verdict = "偏空"
        else:
            stance = "neutral"
            verdict = "中性观望"

        return {
            "symbol": symbol,
            "market": market,
            "stance": stance,
            "one_line_verdict": verdict,
            "window_days": _WINDOW_DAYS,
            "factors": factors,
            "report_citations": report_citations,
            "trace_note": "点击因子查看分位；研报区展示封存时可引用的原文摘要",
            "confidence": min(0.88, 0.45 + 0.08 * len(factors) + (0.05 if report_citations else 0)),
            "evidence": ["kline_history", "quote", "indicators"]
            + (["yanbao_items"] if report_citations else []),
        }
