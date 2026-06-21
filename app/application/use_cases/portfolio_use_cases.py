from __future__ import annotations
"""Portfolio-related UseCases."""


from ..use_cases import UseCase, UseCaseResult


class GetPortfolioUseCase(UseCase):
    """UseCase: Get user's portfolio."""

    def __init__(self, portfolio_service):
        self._portfolio_service = portfolio_service

    def execute(self, user_id: int) -> UseCaseResult:
        try:
            portfolio = self._portfolio_service.get_user_portfolio(user_id)
            return UseCaseResult.ok(portfolio)
        except Exception as e:
            return UseCaseResult.fail(f"获取组合失败: {e}")


class GetPortfolioPositionsUseCase(UseCase):
    """UseCase: Get portfolio positions."""

    def __init__(self, portfolio_service):
        self._portfolio_service = portfolio_service

    def execute(self, portfolio_id: int) -> UseCaseResult:
        try:
            positions = self._portfolio_service.get_positions(portfolio_id)
            return UseCaseResult.ok({"positions": positions})
        except Exception as e:
            return UseCaseResult.fail(f"获取持仓失败: {e}")


class UpdatePortfolioUseCase(UseCase):
    """UseCase: Update portfolio."""

    def __init__(self, portfolio_service):
        self._portfolio_service = portfolio_service

    def execute(self, portfolio_id: int, **updates) -> UseCaseResult:
        try:
            self._portfolio_service.update_portfolio(portfolio_id, **updates)
            return UseCaseResult.ok({"message": "updated"})
        except Exception as e:
            return UseCaseResult.fail(f"更新组合失败: {e}")


class GetPortfolioPerformanceUseCase(UseCase):
    """UseCase: Get portfolio performance metrics."""

    def __init__(self, portfolio_service):
        self._portfolio_service = portfolio_service

    def execute(self, portfolio_id: int, start_date: str | None = None, end_date: str | None = None) -> UseCaseResult:
        try:
            performance = self._portfolio_service.get_performance(portfolio_id, start_date, end_date)
            return UseCaseResult.ok(performance)
        except Exception as e:
            return UseCaseResult.fail(f"获取绩效失败: {e}")