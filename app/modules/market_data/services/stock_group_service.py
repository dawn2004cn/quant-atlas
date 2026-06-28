from __future__ import annotations
"""Stock group application service."""


from app.domain.ports import StockGroupRepository


class StockGroupApplicationService:
    """Use cases around user-defined stock groups."""

    def __init__(self, repository: StockGroupRepository):
        self._repository = repository

    def list_groups(self, user_id: int = 1) -> list[dict]:
        return self._repository.list_groups(user_id=user_id)

    def create_group(self, name: str, description: str = "", color: str = "", user_id: int = 1) -> tuple[bool, str, dict | None]:
        if not name:
            return False, "分组名称不能为空", None
        if name == "自选股":
            return False, "不能创建名为自选股的分组", None
        created = self._repository.create_group(name, description, color, user_id=user_id)
        if not created:
            return False, "分组已存在", None
        return True, "创建成功", created

    def update_group(self, group_id: int, name: str, description: str = "", color: str = "", user_id: int = 1) -> tuple[bool, str]:
        if not name:
            return False, "分组名称不能为空"
        if not self._repository.update_group(group_id, name, description, color, user_id=user_id):
            return False, "更新失败"
        return True, "更新成功"

    def delete_group(self, group_id: int, user_id: int = 1) -> tuple[bool, str]:
        if not self._repository.delete_group(group_id, user_id=user_id):
            return False, "删除失败"
        return True, "删除成功"

    def list_group_symbols(self, group_id: int, user_id: int = 1) -> list[str]:
        return self._repository.list_group_symbols(group_id, user_id=user_id)

    def add_symbol(self, group_id: int, symbol: str, user_id: int = 1) -> tuple[bool, str]:
        if not symbol:
            return False, "股票代码不能为空"
        if not self._repository.add_symbol_to_group(group_id, symbol, user_id=user_id):
            return False, "添加失败"
        return True, "添加成功"

    def remove_symbol(self, group_id: int, symbol: str, user_id: int = 1) -> tuple[bool, str]:
        if not symbol:
            return False, "股票代码不能为空"

        from app.domain.shared.symbol_normalizer import SymbolNormalizer
        normalized = SymbolNormalizer.to_db_code(symbol)

        # Check if symbol exists in group
        existing = self._repository.list_group_symbols(group_id, user_id=user_id)
        if normalized not in existing:
            return False, f"股票 {symbol} 不在当前分组中"

        if not self._repository.remove_symbol_from_group(group_id, symbol, user_id=user_id):
            return False, "移除失败，请重试"
        return True, "移除成功"

    def clear_group(self, group_id: int, user_id: int = 1) -> tuple[bool, str]:
        symbols = self._repository.list_group_symbols(group_id, user_id=user_id)
        for sym in symbols:
            self._repository.remove_symbol_from_group(group_id, sym, user_id=user_id)
        return True, f"已清空 {len(symbols)} 个股票"
