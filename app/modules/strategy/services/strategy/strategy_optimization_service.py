from __future__ import annotations

"""Strategy optimization application service."""


from app.application.dto.strategy_dto import WalkForwardResultDTO, WalkForwardWindowDTO
from app.core.base_service import BaseApplicationService
from app.domain.ports import MarketDataProvider
from app.domain.ports.strategy_ports import WalkForwardOptimizerPort
from app.modules.system.services.helpers.strategy_access import create_default_walk_forward_optimizer


class StrategyOptimizationService(BaseApplicationService):
    """Application service for strategy parameter optimization."""

    def __init__(
        self,
        market_provider: MarketDataProvider | None = None,
        optimizer: WalkForwardOptimizerPort | None = None,
    ):
        super().__init__()
        self._market_provider = market_provider
        self._optimizer = optimizer or create_default_walk_forward_optimizer()

    def run_walk_forward(
        self,
        symbol: str,
        param_space: dict[str, list[float]],
        start_date: str,
        end_date: str,
        objective: str = "sharpe_ratio",
        train_window_days: int = 252,
        test_window_days: int = 63,
        n_windows: int = 5,
    ) -> WalkForwardResultDTO:
        from app.domain.enums import MarketCode
        market = MarketCode.CN

        history = self._market_provider.get_stock_history(symbol, market, start_date, end_date)

        if not history:
            self.logger.warning(f"No historical data found for {symbol} to run walk forward.")
            return WalkForwardResultDTO(
                strategy_name="",
                symbol=symbol,
                param_space=param_space,
                optimal_params={},
                windows=[],
                avg_train_return=0.0,
                avg_test_return=0.0,
                in_sample_score=0.0,
                out_sample_score=0.0,
                stability_score=0.0,
                conclusion=f"No historical data found for {symbol}",
            )

        result = self._optimizer.optimize(
            data=history,
            param_space=param_space,
            objective=objective,
            train_window_days=train_window_days,
            test_window_days=test_window_days,
            n_windows=n_windows,
        )

        window_dtos = [
            WalkForwardWindowDTO(
                train_start=w.train_start,
                train_end=w.train_end,
                test_start=w.test_start,
                test_end=w.test_end,
                train_return=w.train_return,
                test_return=w.test_return,
                params=w.params,
            )
            for w in result.windows
        ]

        return WalkForwardResultDTO(
            strategy_name="WalkForward",
            symbol=symbol,
            param_space=param_space,
            optimal_params=result.optimal_params,
            windows=window_dtos,
            avg_train_return=result.avg_train_return,
            avg_test_return=result.avg_test_return,
            in_sample_score=result.in_sample_score,
            out_sample_score=result.out_sample_score,
            stability_score=result.stability_score,
            conclusion=result.conclusion,
        )
