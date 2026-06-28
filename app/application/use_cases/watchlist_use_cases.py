from __future__ import annotations
"""Watchlist-related UseCases."""


from ..use_cases import UseCase, UseCaseResult


class GetWatchlistUseCase(UseCase):
    """UseCase: Get user's watchlist."""

    def __init__(self, watchlist_service):
        self._watchlist_service = watchlist_service

    def execute(self, user_id: int | None = None, group_id: int | None = None) -> UseCaseResult:
        try:
            if group_id:
                stocks = self._watchlist_service.get_group_stocks(group_id)
            else:
                stocks = self._watchlist_service.get_user_watchlist(user_id)
            return UseCaseResult.ok({"stocks": stocks, "count": len(stocks)})
        except Exception as e:
            return UseCaseResult.fail(f"获取自选股失败: {e}")


class AddToWatchlistUseCase(UseCase):
    """UseCase: Add stock to watchlist."""

    def __init__(self, watchlist_service):
        self._watchlist_service = watchlist_service

    def execute(self, user_id: int, code: str, group_id: int = 1) -> UseCaseResult:
        try:
            self._watchlist_service.add_stock(user_id, code, group_id)
            return UseCaseResult.ok({"message": "added"})
        except Exception as e:
            return UseCaseResult.fail(f"添加自选失败: {e}")


class RemoveFromWatchlistUseCase(UseCase):
    """UseCase: Remove stock from watchlist."""

    def __init__(self, watchlist_service):
        self._watchlist_service = watchlist_service

    def execute(self, user_id: int, code: str, group_id: int = 1) -> UseCaseResult:
        try:
            self._watchlist_service.remove_stock(user_id, code, group_id)
            return UseCaseResult.ok({"message": "removed"})
        except Exception as e:
            return UseCaseResult.fail(f"删除自选失败: {e}")


class GetWatchlistGroupsUseCase(UseCase):
    """UseCase: Get user's watchlist groups."""

    def __init__(self, watchlist_service):
        self._watchlist_service = watchlist_service

    def execute(self, user_id: int) -> UseCaseResult:
        try:
            groups = self._watchlist_service.get_user_groups(user_id)
            return UseCaseResult.ok({"groups": groups})
        except Exception as e:
            return UseCaseResult.fail(f"获取分组失败: {e}")
