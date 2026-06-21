"""Backtest facade response DTOs."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class BacktestResultDTO(BaseModel):
    """Normalized backtest output for API and task consumers."""

    model_config = ConfigDict(extra="allow")

    status: str = "ok"
    symbol: str | None = None
    strategy_name: str | None = None
    total_return: float | None = None
    annual_return: float | None = None
    sharpe: float | None = None
    max_drawdown: float | None = None
    max_drawdown_pct: float | None = None
    win_rate: float | None = None
    equity_curve: list[dict[str, Any]] = Field(default_factory=list)
    mlflow_run_id: str | None = None
    mlflow_model_name: str | None = None
    mlflow_model_version: str | None = None
    error: str | None = None

    @classmethod
    def from_service(cls, payload: Any) -> BacktestResultDTO:
        if hasattr(payload, "model_dump"):
            data: dict[str, Any] = payload.model_dump()
        elif isinstance(payload, dict):
            data = dict(payload)
        else:
            data = {"result": payload}

        if data.get("sharpe") is None and data.get("sharpe_ratio") is not None:
            data["sharpe"] = data["sharpe_ratio"]
        if data.get("max_drawdown") is None and data.get("max_drawdown_pct") is not None:
            data["max_drawdown"] = data["max_drawdown_pct"]
        if data.get("max_drawdown_pct") is None and data.get("max_drawdown") is not None:
            try:
                md = float(data["max_drawdown"])
            except (TypeError, ValueError):
                md = None
            if md is not None:
                data["max_drawdown_pct"] = abs(md) * 100 if abs(md) <= 1 else abs(md)
        if data.get("win_rate") is None and data.get("winrate") is not None:
            data["win_rate"] = data["winrate"]
        if data.get("equity_curve") is None and data.get("equity") is not None:
            curve = data["equity"]
            data["equity_curve"] = curve if isinstance(curve, list) else []

        return cls.model_validate(data)
