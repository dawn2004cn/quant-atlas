from __future__ import annotations

from typing import Any

from pydantic import ValidationError as PydanticValidationError

from app.application.dto.market_data_dto import BacktestCompareRequestDTO, BacktestRequestDTO, SelectionRequestDTO
from app.application.errors import ValidationError
from app.domain.enums import MarketCode
from app.facade._helpers import observe_facade, parse_market, validation_error_from_pydantic
from app.facade.dto.backtest_facade_dto import BacktestResultDTO
from app.infrastructure.mlflow.backtest_log_hook import attach_mlflow_run_id


class BacktestFacade:
    """Facade for backtesting operations."""

    _FACADE_NAME = "backtest"

    def __init__(self, strategy_service: Any):
        self._strategy_service = strategy_service

    def run_backtest(
        self,
        *,
        symbol: str,
        strategy_name: str,
        start: str,
        end: str,
        initial_capital: float = 100000.0,
    ) -> dict[str, Any]:
        """Validate input and delegate to the strategy service backtest engine."""
        with observe_facade(self._FACADE_NAME, "run_backtest"):
            if self._strategy_service is None:
                raise ValidationError("Strategy service not configured")

            try:
                dto = BacktestRequestDTO(
                    symbol=symbol,
                    strategy_name=strategy_name,
                    start=start,
                    end=end,
                    initial_capital=initial_capital,
                )
            except PydanticValidationError as exc:
                raise validation_error_from_pydantic(exc) from exc

            result = self._strategy_service.backtest(
                symbol=dto.symbol,
                strategy_name=dto.strategy_name,
                start=dto.start,
                end=dto.end,
                initial_capital=dto.initial_capital,
            )
            normalized = self._normalize_backtest_result(result)
            return attach_mlflow_run_id(
                normalized,
                symbol=dto.symbol,
                strategy_name=dto.strategy_name,
                start=dto.start,
                end=dto.end,
                initial_capital=dto.initial_capital,
            )

    def compare_strategies(
        self,
        *,
        symbol: str,
        strategies: list[str],
        start: str,
        end: str,
        initial_capital: float = 100000.0,
    ) -> dict[str, Any]:
        """Run the same symbol/period backtest for multiple strategies and rank by return."""
        with observe_facade(self._FACADE_NAME, "compare_strategies"):
            if self._strategy_service is None:
                raise ValidationError("Strategy service not configured")

            try:
                dto = BacktestCompareRequestDTO(
                    symbol=symbol,
                    strategies=strategies,
                    start=start,
                    end=end,
                    initial_capital=initial_capital,
                )
            except PydanticValidationError as exc:
                raise validation_error_from_pydantic(exc) from exc

            rows: list[dict[str, Any]] = []
            for strategy_name in dto.strategies:
                try:
                    result = self.run_backtest(
                        symbol=dto.symbol,
                        strategy_name=strategy_name,
                        start=dto.start,
                        end=dto.end,
                        initial_capital=dto.initial_capital,
                    )
                    rows.append(self._compare_row(strategy_name, result))
                except ValidationError as exc:
                    rows.append(
                        {
                            "strategy_name": strategy_name,
                            "status": "error",
                            "error": str(exc),
                        }
                    )

            ok_rows = [r for r in rows if r.get("status") == "ok"]
            winner = None
            if ok_rows:
                winner = max(
                    ok_rows,
                    key=lambda r: (
                        float(r.get("total_return") or 0.0),
                        float(r.get("sharpe") or 0.0),
                    ),
                ).get("strategy_name")

            return {
                "symbol": dto.symbol,
                "start": dto.start,
                "end": dto.end,
                "initial_capital": dto.initial_capital,
                "comparisons": rows,
                "winner": winner,
            }

    @staticmethod
    def _compare_row(strategy_name: str, result: dict[str, Any]) -> dict[str, Any]:
        metrics = result.get("metrics") if isinstance(result.get("metrics"), dict) else {}
        total_return = result.get("total_return", metrics.get("total_return"))
        sharpe = result.get("sharpe", result.get("sharpe_ratio", metrics.get("sharpe")))
        max_drawdown = result.get("max_drawdown", metrics.get("max_drawdown"))
        annual_return = result.get("annual_return", metrics.get("annual_return"))
        win_rate = result.get("win_rate", metrics.get("win_rate"))
        trade_count = result.get("trade_count", metrics.get("trade_count"))
        return {
            "strategy_name": strategy_name,
            "status": "ok",
            "total_return": total_return,
            "annual_return": annual_return,
            "sharpe": sharpe,
            "max_drawdown": max_drawdown,
            "win_rate": win_rate,
            "trade_count": trade_count,
            "mlflow_run_id": result.get("mlflow_run_id"),
        }

    def run_backtest_async(
        self,
        *,
        symbol: str,
        strategy_name: str,
        start: str,
        end: str,
        initial_capital: float = 100000.0,
    ) -> dict[str, Any]:
        """Queue a backtest via Celery when available; otherwise run synchronously."""
        with observe_facade(self._FACADE_NAME, "run_backtest_async"):
            try:
                dto = BacktestRequestDTO(
                    symbol=symbol,
                    strategy_name=strategy_name,
                    start=start,
                    end=end,
                    initial_capital=initial_capital,
                )
            except PydanticValidationError as exc:
                raise validation_error_from_pydantic(exc) from exc

            from app.tasks.backtest_tasks import submit_strategy_backtest

            return submit_strategy_backtest(
                symbol=dto.symbol,
                strategy_name=dto.strategy_name,
                start=dto.start,
                end=dto.end,
                initial_capital=dto.initial_capital,
            )

    def select_stocks(
        self,
        *,
        strategy_name: str,
        market: str | MarketCode,
        top_n: int = 20,
    ) -> dict[str, Any]:
        """Validate selection params and delegate to strategy service."""
        with observe_facade(self._FACADE_NAME, "select_stocks"):
            if self._strategy_service is None:
                raise ValidationError("Strategy service not configured")

            mc = parse_market(market)
            try:
                dto = SelectionRequestDTO(
                    strategy=strategy_name,
                    market=mc.value,
                    top_n=top_n,
                )
            except PydanticValidationError as exc:
                raise validation_error_from_pydantic(exc) from exc

            result = self._strategy_service.select_stocks(
                strategy_name=dto.strategy,
                market=mc,
                top_n=dto.top_n,
            )
            if isinstance(result, dict) and result.get("error"):
                raise ValidationError(str(result["error"]))
            if isinstance(result, dict):
                return result
            if hasattr(result, "model_dump"):
                return result.model_dump()
            return {"candidates": result}

    @staticmethod
    def _normalize_backtest_result(result: Any) -> BacktestResultDTO:
        if isinstance(result, dict) and result.get("error"):
            raise ValidationError(str(result["error"]))
        return BacktestResultDTO.from_service(result)
