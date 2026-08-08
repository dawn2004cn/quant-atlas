from __future__ import annotations

from pathlib import Path
from typing import Any

from app.core.logger import get_logger
from app.domain.dto.service_result import GenericResponseDTO
from app.domain.enums import MarketCode

logger = get_logger(__name__)


class QlibBacktestService:
    """Qlib 回测门面 — 优先委托 ``QlibPipelineService`` / ``QlibService``，不可用时标注 ``meta.demo``。"""

    def __init__(
        self,
        base_dir: Path,
        *,
        pipeline_service: Any | None = None,
        qlib_service: Any | None = None,
    ) -> None:
        self._base_dir = base_dir
        self._pipeline = pipeline_service
        self._qlib = qlib_service

    def _demo_payload(self, payload: dict[str, Any], *, reason: str) -> GenericResponseDTO:
        out = dict(payload)
        meta = dict(out.get("meta") or {})
        meta.setdefault("demo", True)
        meta.setdefault("reason", reason)
        out["meta"] = meta
        out.setdefault(
            "disclaimer",
            "演示回测结果；请通过 Qlib 管线或策略回测引擎获取真实绩效。",
        )
        return out

    def simple_backtest(
        self,
        strategy: str,
        symbols: list[str],
        start_date: str,
        end_date: str,
    ) -> GenericResponseDTO:
        pipeline = self._pipeline
        if pipeline is not None and symbols:
            try:
                result = pipeline.simple_backtest(
                    symbols[0],
                    MarketCode.CN,
                    start=start_date,
                    end=end_date,
                )
                if isinstance(result, dict):
                    result.setdefault("strategy", strategy)
                    return result
            except Exception as exc:
                logger.warning("simple_backtest delegation failed: %s", exc, exc_info=True)

        return self._demo_payload(
            {
                "strategy": strategy,
                "symbols": symbols,
                "start_date": start_date,
                "end_date": end_date,
                "total_return": 0.0,
                "sharpe_ratio": 0.0,
            },
            reason="pipeline_unavailable",
        )

    def run_backtest(
        self,
        strategy: str,
        symbols: list[str],
        params: dict[str, Any],
    ) -> GenericResponseDTO:
        qlib = self._qlib
        if qlib is not None and hasattr(qlib, "run_qlib_backtest"):
            cfg = dict(params)
            cfg.setdefault("strategy", params.get("strategy_config") or params.get("strategy"))
            if cfg.get("strategy"):
                try:
                    result = qlib.run_qlib_backtest(cfg)
                    if isinstance(result, dict) and result.get("ok"):
                        return result
                except Exception as exc:
                    logger.warning("run_qlib_backtest delegation failed: %s", exc, exc_info=True)

        return self._demo_payload(
            {
                "strategy": strategy,
                "symbols": symbols,
                "params": params,
                "results": {},
            },
            reason="qlib_runtime_unavailable",
        )

    def unified_buy_hold_backtest(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
    ) -> GenericResponseDTO:
        pipeline = self._pipeline
        if pipeline is not None and hasattr(pipeline, "unified_buy_hold_backtest"):
            try:
                return pipeline.unified_buy_hold_backtest(
                    symbol,
                    MarketCode.CN,
                    start=start_date,
                    end=end_date,
                )
            except Exception as exc:
                logger.warning("unified_buy_hold delegation failed: %s", exc, exc_info=True)

        return self._demo_payload(
            {
                "symbol": symbol,
                "start_date": start_date,
                "end_date": end_date,
                "return": 0.0,
            },
            reason="pipeline_unavailable",
        )
