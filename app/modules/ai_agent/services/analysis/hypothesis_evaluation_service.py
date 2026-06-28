from __future__ import annotations

"""Rule-based hypothesis verification for stock analysis (UI-OPT phase 53)."""

from typing import Any

from app.domain.dto.hypothesis_evaluation_dto import (
    HypothesisCatalogItemDTO,
    HypothesisEvaluationDTO,
    HypothesisEvidenceItemDTO,
)
from app.domain.shared.market_fact import build_trace_ref

_CATALOG: tuple[HypothesisCatalogItemDTO, ...] = (
    HypothesisCatalogItemDTO(
        id="rebound_weak_volume",
        label="反弹但量能不足",
        description="价格回升但成交未能有效放大",
    ),
    HypothesisCatalogItemDTO(
        id="uptrend_intact",
        label="上升趋势延续",
        description="均线与动量仍偏多",
    ),
    HypothesisCatalogItemDTO(
        id="oversold_bounce",
        label="超卖后反弹",
        description="RSI 低位后出现修复",
    ),
    HypothesisCatalogItemDTO(
        id="trend_breakdown",
        label="趋势走弱",
        description="价格跌破关键均线或动量转弱",
    ),
    HypothesisCatalogItemDTO(
        id="custom",
        label="自定义假设",
        description="输入你的交易假设，系统将基于指标给出佐证/反驳",
    ),
)


def _safe_float(value: object, default: float = 0.0) -> float:
    try:
        return float(value or default)
    except (TypeError, ValueError):
        return default


def _ev(
    text: str,
    *,
    source: str = "indicator",
    confidence: float = 0.6,
    symbol: str = "",
    market: str = "CN",
    section_id: str = "stockChart",
    field: str = "close",
) -> HypothesisEvidenceItemDTO:
    anchor = "quote" if source == "quote" else "indicator"
    if section_id == "stockChart":
        anchor = "kline"
    return HypothesisEvidenceItemDTO(
        text=text,
        source=source,
        confidence=round(confidence, 2),
        trace_ref=build_trace_ref(
            anchor=anchor,
            section_id=section_id,
            field=field,
            label=text[:80],
            symbol=symbol,
            market=market,
        ),
    )


class HypothesisEvaluationService:
    """Evaluate a user hypothesis against quote + indicator context."""

    def list_catalog(self) -> list[HypothesisCatalogItemDTO]:
        return list(_CATALOG)

    def resolve(
        self,
        *,
        hypothesis_id: str | None = None,
        user_hypothesis: str | None = None,
    ) -> tuple[str, str]:
        hid = (hypothesis_id or "").strip().lower()
        text = (user_hypothesis or "").strip()
        if hid and hid != "custom":
            for item in _CATALOG:
                if item.id == hid:
                    return item.id, text or item.label
        if text:
            return "custom", text
        return "custom", ""

    def evaluate(
        self,
        *,
        symbol: str,
        detail: dict[str, Any],
        hypothesis_id: str | None = None,
        user_hypothesis: str | None = None,
        market: str = "CN",
    ) -> HypothesisEvaluationDTO | None:
        hid, label = self.resolve(hypothesis_id=hypothesis_id, user_hypothesis=user_hypothesis)
        if not label:
            return None
        metrics = self._extract_metrics(detail)
        sym = str(symbol or metrics.get("symbol") or "")
        mkt = (market or "CN").upper()
        if hid == "rebound_weak_volume":
            return self._eval_rebound_weak_volume(hid, label, metrics, sym, mkt)
        if hid == "uptrend_intact":
            return self._eval_uptrend(hid, label, metrics, sym, mkt)
        if hid == "oversold_bounce":
            return self._eval_oversold_bounce(hid, label, metrics, sym, mkt)
        if hid == "trend_breakdown":
            return self._eval_breakdown(hid, label, metrics, sym, mkt)
        return self._eval_custom(hid, label, metrics, sym, mkt)

    @staticmethod
    def _extract_metrics(detail: dict[str, Any]) -> dict[str, float | str]:
        profile = detail.get("profile") or {}
        realtime = profile.get("realtime") or {}
        indicators = detail.get("indicators") or {}
        price = _safe_float(realtime.get("price"))
        change_pct = _safe_float(realtime.get("change_pct"))
        volume = _safe_float(realtime.get("volume"))
        ma5 = _safe_float(indicators.get("ma5") or indicators.get("sma5"))
        ma20 = _safe_float(indicators.get("ma20") or indicators.get("sma20"), price)
        rsi = _safe_float(indicators.get("rsi14") or indicators.get("rsi"), 50.0)
        macd = _safe_float(indicators.get("macd"))
        macd_signal = _safe_float(indicators.get("macd_signal"))
        if not ma5 and ma20:
            ma5 = ma20
        return {
            "symbol": str(detail.get("symbol") or realtime.get("code") or ""),
            "price": price,
            "change_pct": change_pct,
            "volume": volume,
            "ma5": ma5,
            "ma20": ma20,
            "rsi": rsi,
            "macd": macd,
            "macd_signal": macd_signal,
        }

    @staticmethod
    def _finalize(
        hid: str,
        label: str,
        support: list[HypothesisEvidenceItemDTO],
        contradict: list[HypothesisEvidenceItemDTO],
    ) -> HypothesisEvaluationDTO:
        if support and not contradict:
            verdict = "supports"
        elif contradict and not support:
            verdict = "contradicts"
        elif support and contradict:
            verdict = "mixed"
        else:
            verdict = "inconclusive"
        s_conf = sum(x.confidence for x in support) / len(support) if support else 0.0
        c_conf = sum(x.confidence for x in contradict) / len(contradict) if contradict else 0.0
        if verdict == "supports":
            confidence = min(0.95, 0.45 + s_conf * 0.5)
            summary = f"现有指标整体佐证「{label}」。"
        elif verdict == "contradicts":
            confidence = min(0.95, 0.45 + c_conf * 0.5)
            summary = f"现有指标整体反驳「{label}」。"
        elif verdict == "mixed":
            confidence = min(0.9, 0.35 + abs(s_conf - c_conf) * 0.35)
            summary = f"「{label}」同时存在佐证与反驳信号，建议结合量能与新闻进一步确认。"
        else:
            confidence = 0.25
            summary = f"数据不足以判定「{label}」，请补充历史 K 线或新闻上下文。"
        return HypothesisEvaluationDTO(
            hypothesis_id=hid,
            user_hypothesis=label,
            verdict=verdict,
            confidence=round(confidence, 2),
            supporting_evidence=support,
            contradicting_evidence=contradict,
            summary=summary,
        )

    def _eval_rebound_weak_volume(
        self,
        hid: str,
        label: str,
        m: dict[str, float | str],
        sym: str,
        mkt: str,
    ) -> HypothesisEvaluationDTO:
        price = _safe_float(m.get("price"))
        ma20 = _safe_float(m.get("ma20"))
        change_pct = _safe_float(m.get("change_pct"))
        rsi = _safe_float(m.get("rsi"), 50.0)
        support: list[HypothesisEvidenceItemDTO] = []
        contradict: list[HypothesisEvidenceItemDTO] = []
        def ev(*a, **k):
            return _ev(*a, symbol=sym, market=mkt, **k)

        if price > ma20 > 0 or change_pct > 0:
            support.append(ev(f"价格 {price:.2f} 高于 MA20 {ma20:.2f} 或当日涨幅 {change_pct:.2f}%", confidence=0.72, section_id="stock-detail-hero", field="price"))
        else:
            contradict.append(ev(f"价格 {price:.2f} 未站稳 MA20 {ma20:.2f}，涨幅 {change_pct:.2f}%", confidence=0.7, section_id="stock-detail-hero", field="price"))

        weak_volume = change_pct > 0 and abs(change_pct) < 2.5 and 40 <= rsi <= 62
        if weak_volume:
            support.append(ev("涨幅温和且 RSI 中性，量能配合偏弱（代理指标）", confidence=0.65, field="volume"))
        elif change_pct >= 2.5:
            contradict.append(ev(f"当日涨幅 {change_pct:.2f}% 偏高，反弹伴随一定动能", confidence=0.68, field="change_pct"))
        else:
            contradict.append(ev("缺少明确缩量特征，假设中的「量能不足」证据不足", confidence=0.45))

        return self._finalize(hid, label, support, contradict)

    def _eval_uptrend(
        self,
        hid: str,
        label: str,
        m: dict[str, float | str],
        sym: str,
        mkt: str,
    ) -> HypothesisEvaluationDTO:
        price = _safe_float(m.get("price"))
        ma5 = _safe_float(m.get("ma5"))
        ma20 = _safe_float(m.get("ma20"))
        macd = _safe_float(m.get("macd"))
        macd_signal = _safe_float(m.get("macd_signal"))
        support: list[HypothesisEvidenceItemDTO] = []
        contradict: list[HypothesisEvidenceItemDTO] = []
        def ev(*a, **k):
            return _ev(*a, symbol=sym, market=mkt, **k)

        if ma5 > ma20 > 0 and price >= ma20:
            support.append(ev(f"MA5 {ma5:.2f} > MA20 {ma20:.2f}，价格 {price:.2f} 站上 MA20", confidence=0.78, section_id="stockChart"))
        else:
            contradict.append(ev(f"均线结构未呈多头：MA5 {ma5:.2f} / MA20 {ma20:.2f} / 价 {price:.2f}", confidence=0.75, section_id="stockChart"))

        if macd >= macd_signal:
            support.append(ev("MACD 不低于信号线，动量未明显转弱", confidence=0.62, field="macd"))
        else:
            contradict.append(ev("MACD 低于信号线，动量偏弱", confidence=0.64, field="macd"))

        return self._finalize(hid, label, support, contradict)

    def _eval_oversold_bounce(
        self,
        hid: str,
        label: str,
        m: dict[str, float | str],
        sym: str,
        mkt: str,
    ) -> HypothesisEvaluationDTO:
        rsi = _safe_float(m.get("rsi"), 50.0)
        change_pct = _safe_float(m.get("change_pct"))
        price = _safe_float(m.get("price"))
        ma5 = _safe_float(m.get("ma5"))
        support: list[HypothesisEvidenceItemDTO] = []
        contradict: list[HypothesisEvidenceItemDTO] = []
        def ev(*a, **k):
            return _ev(*a, symbol=sym, market=mkt, **k)

        if rsi <= 38:
            support.append(ev(f"RSI {rsi:.1f} 处于偏低区域，存在超卖修复基础", confidence=0.7, field="rsi"))
        else:
            contradict.append(ev(f"RSI {rsi:.1f} 未处低位，「超卖」前提较弱", confidence=0.66, field="rsi"))

        if change_pct > 0 or (ma5 > 0 and price >= ma5):
            support.append(ev(f"当日修复：涨幅 {change_pct:.2f}% / 价格相对 MA5", confidence=0.63, section_id="stock-detail-hero"))
        else:
            contradict.append(ev(f"当日仍偏弱，涨幅 {change_pct:.2f}%", confidence=0.67, section_id="stock-detail-hero"))

        return self._finalize(hid, label, support, contradict)

    def _eval_breakdown(
        self,
        hid: str,
        label: str,
        m: dict[str, float | str],
        sym: str,
        mkt: str,
    ) -> HypothesisEvaluationDTO:
        price = _safe_float(m.get("price"))
        ma5 = _safe_float(m.get("ma5"))
        ma20 = _safe_float(m.get("ma20"))
        change_pct = _safe_float(m.get("change_pct"))
        support: list[HypothesisEvidenceItemDTO] = []
        contradict: list[HypothesisEvidenceItemDTO] = []
        def ev(*a, **k):
            return _ev(*a, symbol=sym, market=mkt, **k)

        if price < ma20 or ma5 < ma20:
            support.append(ev(f"价格 {price:.2f} 或 MA5 {ma5:.2f} 低于 MA20 {ma20:.2f}", confidence=0.76, section_id="stockChart"))
        else:
            contradict.append(ev(f"价格与 MA5 仍守在 MA20 {ma20:.2f} 上方", confidence=0.72, section_id="stockChart"))

        if change_pct < 0:
            support.append(ev(f"当日涨跌幅 {change_pct:.2f}% 为负", confidence=0.6, field="change_pct"))
        else:
            contradict.append(ev(f"当日涨跌幅 {change_pct:.2f}% 未走弱", confidence=0.58, field="change_pct"))

        return self._finalize(hid, label, support, contradict)

    def _eval_custom(
        self,
        hid: str,
        label: str,
        m: dict[str, float | str],
        sym: str,
        mkt: str,
    ) -> HypothesisEvaluationDTO:
        support: list[HypothesisEvidenceItemDTO] = []
        contradict: list[HypothesisEvidenceItemDTO] = []
        price = _safe_float(m.get("price"))
        ma20 = _safe_float(m.get("ma20"))
        rsi = _safe_float(m.get("rsi"), 50.0)
        change_pct = _safe_float(m.get("change_pct"))
        def ev(*a, **k):
            return _ev(*a, symbol=sym, market=mkt, **k)

        if any(k in label for k in ("反弹", "回升", "修复")):
            if change_pct > 0 or price > ma20:
                support.append(ev("自定义假设含「反弹/修复」：价格或涨幅偏多", confidence=0.6))
            else:
                contradict.append(ev("自定义假设含「反弹/修复」：但价格/涨幅未配合", confidence=0.6))
        if any(k in label for k in ("量能", "缩量", "放量")):
            if change_pct > 0 and abs(change_pct) < 2.5:
                support.append(ev("自定义假设含「量能」：当日涨幅温和，量能或偏弱", confidence=0.55))
            elif abs(change_pct) >= 2.5:
                contradict.append(ev("自定义假设含「量能」：当日波动偏大，与缩量描述不一致", confidence=0.55))
        if any(k in label for k in ("超卖", "低位")):
            if rsi <= 40:
                support.append(ev(f"自定义假设含「超卖/低位」：RSI {rsi:.1f}", confidence=0.58, field="rsi"))
            else:
                contradict.append(ev(f"自定义假设含「超卖/低位」：RSI {rsi:.1f} 未处低位", confidence=0.58, field="rsi"))
        if any(k in label for k in ("走弱", "下跌", "跌破")):
            if price < ma20 or change_pct < 0:
                support.append(ev("自定义假设含「走弱/下跌」：价格或涨幅偏空", confidence=0.58))
            else:
                contradict.append(ev("自定义假设含「走弱/下跌」：均线/涨幅未确认", confidence=0.58))

        if not support and not contradict:
            support.append(ev(f"已记录假设「{label}」，当前 RSI {rsi:.1f}、涨幅 {change_pct:.2f}%", confidence=0.35))

        return self._finalize(hid, label, support, contradict)


__all__ = ["HypothesisEvaluationService"]
