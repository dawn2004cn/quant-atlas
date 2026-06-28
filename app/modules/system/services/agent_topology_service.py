from __future__ import annotations

"""Agent 团队拓扑：基于 30 日归因与市场状态动态调权。"""

import json
import statistics
import threading
from datetime import date, timedelta
from typing import Any

from app.config import BASE_DIR
from app.core.logger import get_logger

logger = get_logger(__name__)

_DEFAULT_WEIGHTS: dict[str, float] = {
    "macro_analyst": 1.0,
    "fundamental_analyst": 1.0,
    "technical_analyst": 1.0,
    "sentiment_analyst": 1.0,
    "backtest_optimizer": 1.0,
    "bull": 1.0,
    "bear": 1.0,
}

_lock = threading.Lock()
_STATE_PATH = BASE_DIR / "instance" / "agent_topology.json"


class AgentTopologyService:
    """Adjust research agent weights from 30d attribution + regime."""

    def __init__(self, *, stock_service: Any | None = None) -> None:
        self._stock_service = stock_service

    def compute_topology(
        self,
        symbol: str,
        *,
        market: str = "CN",
        period: str = "30d",
    ) -> dict[str, Any]:
        sym = (symbol or "600519").strip().upper()
        regime = self._infer_regime(sym, market)
        attribution = self._load_attribution_summary(sym, period)
        weights = self._adjust_weights(regime, attribution)
        payload = {
            "symbol": sym,
            "market": market.upper(),
            "period": period,
            "regime": regime,
            "attribution_summary": attribution,
            "agent_weights": weights,
            "topology_notes": self._notes(regime, attribution),
        }
        self._persist(payload)
        return payload

    def get_cached(self, symbol: str | None = None) -> dict[str, Any]:
        with _lock:
            if not _STATE_PATH.is_file():
                return {}
            try:
                data = json.loads(_STATE_PATH.read_text(encoding="utf-8"))
            except Exception:
                return {}
        if symbol:
            return data.get(symbol.upper()) or {}
        return data

    def _infer_regime(self, symbol: str, market: str) -> str:
        bars = self._fetch_bars(symbol, market, days=30)
        if len(bars) < 8:
            return "unknown"
        closes = [float(b.get("close") or b.get("Close") or 0) for b in bars if b]
        closes = [c for c in closes if c > 0]
        if len(closes) < 8:
            return "unknown"
        total_ret = (closes[-1] - closes[0]) / closes[0] * 100.0
        daily = [(closes[i] - closes[i - 1]) / closes[i - 1] for i in range(1, len(closes))]
        vol = statistics.pstdev(daily) * 100.0 * (252 ** 0.5) if len(daily) > 1 else 0.0
        if abs(total_ret) >= 8.0 and vol < 40.0:
            return "trending"
        if vol >= 28.0 and abs(total_ret) < 5.0:
            return "ranging"
        return "mixed"

    def _fetch_bars(self, symbol: str, market: str, *, days: int) -> list[dict[str, Any]]:
        if self._stock_service is None:
            return []
        end_d = date.today()
        start_d = end_d - timedelta(days=days)
        try:
            return self._stock_service.get_history(
                symbol, market, start_d.isoformat(), end_d.isoformat()
            ) or []
        except Exception as exc:
            logger.debug("agent_topology history fetch failed: %s", exc)
            return []

    def _load_attribution_summary(self, symbol: str, period: str) -> dict[str, Any]:
        try:
            from app.modules.strategy.services.analytics.unified_attribution_service import (
                UnifiedAttributionService,
            )

            svc = UnifiedAttributionService()
            report = svc.build_report(
                strategy_name="agent_topology",
                period=period,
                positions=[{"symbol": symbol, "name": symbol, "value": 100000, "return_pct": 0}],
                symbol=symbol,
                include_slippage=False,
            )
            alpha = float(report.market_effect.alpha or 0)
            total = float(report.total_return or 0)
            top_factor = report.factors[0].factor_name if report.factors else ""
            return {
                "total_return_pct": total,
                "alpha": alpha,
                "top_factor": top_factor,
                "factor_count": len(report.factors),
            }
        except Exception as exc:
            logger.debug("agent_topology attribution: %s", exc)
            return {"total_return_pct": 0.0, "alpha": 0.0, "top_factor": "", "factor_count": 0}

    def _adjust_weights(self, regime: str, attribution: dict[str, Any]) -> dict[str, float]:
        weights = dict(_DEFAULT_WEIGHTS)
        if regime == "trending":
            weights["technical_analyst"] = 1.35
            weights["backtest_optimizer"] = 1.2
            weights["macro_analyst"] = 0.9
        elif regime == "ranging":
            weights["technical_analyst"] = 1.25
            weights["backtest_optimizer"] = 1.35
            weights["sentiment_analyst"] = 1.1
        alpha = float(attribution.get("alpha") or 0)
        if alpha > 1.0:
            weights["fundamental_analyst"] = 1.2
        elif alpha < -1.0:
            weights["bear"] = 1.15
            weights["bull"] = 0.9
        return {k: round(v, 3) for k, v in weights.items()}

    @staticmethod
    def _notes(regime: str, attribution: dict[str, Any]) -> list[str]:
        notes = [f"市场状态推断: {regime}"]
        if attribution.get("top_factor"):
            notes.append(f"主导因子: {attribution['top_factor']}")
        if regime == "ranging":
            notes.append("震荡市：提升均值回归与回测优化 Agent 权重")
        elif regime == "trending":
            notes.append("单边市：提升趋势跟踪与技术 Analyst 权重")
        return notes

    def _persist(self, payload: dict[str, Any]) -> None:
        sym = str(payload.get("symbol") or "").upper()
        if not sym:
            return
        with _lock:
            all_rows: dict[str, Any] = {}
            if _STATE_PATH.is_file():
                try:
                    all_rows = json.loads(_STATE_PATH.read_text(encoding="utf-8"))
                except Exception:
                    all_rows = {}
            all_rows[sym] = payload
            _STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
            _STATE_PATH.write_text(json.dumps(all_rows, ensure_ascii=False, indent=2), encoding="utf-8")
