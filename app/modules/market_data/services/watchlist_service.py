from __future__ import annotations

from app.core.logger import get_logger
from app.domain.dto.service_result import GenericResponseDTO
from app.domain.dto.watchlist_dto import QuoteItem, WatchlistResponse

import json
import threading
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

from app.domain.enums import MarketCode
from app.domain.ports import MarketDataProvider, StockGroupRepository, WatchlistRepository
from app.modules.system.services.helpers.stock_metadata import get_stock_metadata_batch
from app.domain.shared.symbol_normalizer import SymbolNormalizer

logger = get_logger(__name__)


class SortBy(str, Enum):
    ADD_TIME = "add_time"
    CHANGE_PCT = "change_pct"
    PRICE = "price"
    NAME = "name"
    INDUSTRY = "industry"


class WatchlistApplicationService:
    """Use cases around watchlist management."""

    def __init__(
        self,
        repository: WatchlistRepository,
        stock_group_repository: StockGroupRepository | None = None,
        market_provider: MarketDataProvider | None = None,
        price_alert_store_path: str | Path | None = None,
    ):
        self._repository = repository
        self._stock_group_repository = stock_group_repository
        self._market_provider = market_provider
        self._price_alert_lock = threading.Lock()
        self._price_alert_store_path = Path(price_alert_store_path) if price_alert_store_path else None
        if self._price_alert_store_path:
            self._price_alert_store_path.parent.mkdir(parents=True, exist_ok=True)
        self._price_alerts: dict[str, dict[str, dict[str, Any]]] = self._read_price_alerts()

    def list_symbols(self, user_id: int) -> list[str]:
        return self._repository.list_symbols(user_id=user_id)

    def add_symbol(self, user_id: int, symbol: str) -> list[str]:
        current = self._repository.list_symbols(user_id=user_id)
        from app.domain.shared.symbol_normalizer import SymbolNormalizer
        normalized = SymbolNormalizer.to_db_code(symbol)
        if normalized not in current:
            current.append(normalized)
            self._repository.save_symbols(user_id, current)
        return current

    def remove_symbol(self, user_id: int, symbol: str) -> list[str]:
        current = self._repository.list_symbols(user_id=user_id)
        from app.domain.shared.symbol_normalizer import SymbolNormalizer
        normalized = SymbolNormalizer.to_db_code(symbol)
        if normalized in current:
            current.remove(normalized)
            self._repository.save_symbols(user_id, current)
        return current

    def batch_add_symbols(self, user_id: int, symbols: list[str]) -> tuple[bool, str, list[str]]:
        if not symbols:
            return False, "股票列表为空", []
        current = self._repository.list_symbols(user_id=user_id)
        from app.domain.shared.symbol_normalizer import SymbolNormalizer
        added = []
        duplicates = []
        for sym in symbols:
            normalized = SymbolNormalizer.to_db_code(sym)
            if normalized not in current and normalized not in added:
                added.append(normalized)
            elif normalized in current:
                duplicates.append(normalized)
        if added:
            current.extend(added)
            self._repository.save_symbols(user_id, current)
        msg = f"成功添加 {len(added)} 只股票"
        if duplicates:
            msg += f"，{len(duplicates)} 只已存在"
        return True, msg, current

    def batch_remove_symbols(self, user_id: int, symbols: list[str]) -> tuple[bool, str, list[str]]:
        if not symbols:
            return False, "股票列表为空", []
        current = self._repository.list_symbols(user_id=user_id)
        from app.domain.shared.symbol_normalizer import SymbolNormalizer
        removed = []
        not_found = []
        for sym in symbols:
            normalized = SymbolNormalizer.to_db_code(sym)
            if normalized in current:
                current.remove(normalized)
                removed.append(normalized)
            else:
                not_found.append(normalized)
        self._repository.save_symbols(user_id, current)
        msg = f"成功移除 {len(removed)} 只股票"
        if not_found:
            msg += f"，{len(not_found)} 只不存在"
        return True, msg, current

    def create_watchlist(self, user_id: int, name: str, description: str = "") -> tuple[bool, str, dict | None]:
        if not self._stock_group_repository:
            return False, "分组服务未初始化", None
        if not name:
            return False, "分组名称不能为空", None
        if name == "自选股":
            return False, "不能创建名为自选股的分组", None
        group = self._stock_group_repository.create_group(name, description, user_id=user_id)
        if not group:
            return False, "分组已存在", None
        return True, "创建成功", group

    def delete_watchlist(self, user_id: int, name: str) -> tuple[bool, str]:
        if not self._stock_group_repository:
            return False, "分组服务未初始化"
        groups = self._stock_group_repository.list_groups(user_id=user_id)
        target = next((g for g in groups if g["name"] == name and not g.get("is_default")), None)
        if not target:
            return False, "分组不存在或为系统默认分组"
        if self._stock_group_repository.delete_group(target["id"], user_id=user_id):
            return True, "删除成功"
        return False, "删除失败"

    def get_all_watchlists(self, user_id: int) -> GenericResponseDTO[str, list[str]]:
        if not self._stock_group_repository:
            symbols = self._repository.list_symbols(user_id=user_id)
            return {"自选股": symbols} if symbols else {}
        groups = self._stock_group_repository.list_groups(user_id=user_id)
        result = {}
        for group in groups:
            symbols = self._stock_group_repository.list_group_symbols(group["id"], user_id=user_id)
            result[group["name"]] = symbols
        return result

    def get_sorted_quotes(
        self,
        user_id: int,
        group_name: str | None = None,
        sort_by: SortBy = SortBy.ADD_TIME,
        ascending: bool = True,
        page: int = 1,
        page_size: int = 50,
    ) -> WatchlistResponse:
        """Refactored entry point for getting sorted quotes."""
        symbols = self._fetch_symbols(user_id, group_name)
        if not symbols:
            return WatchlistResponse(items=[], total=0, page=page, page_size=page_size, pages=0)

        items = self._fetch_and_enrich_quotes(symbols)

        # Apply sorting
        self._apply_sorting(items, sort_by, ascending)

        # Apply pagination
        return self._apply_pagination(items, page, page_size)

    def _fetch_symbols(self, user_id: int, group_name: str | None) -> list[str]:
        if group_name and self._stock_group_repository:
            groups = self._stock_group_repository.list_groups(user_id=user_id)
            target = next((g for g in groups if g["name"] == group_name), None)
            return self._stock_group_repository.list_group_symbols(target["id"], user_id=user_id) if target else []
        return self._repository.list_symbols(user_id=user_id)

    def _fetch_and_enrich_quotes(self, symbols: list[str]) -> list[QuoteItem]:
        items = []
        if not self._market_provider:
            return [QuoteItem(code=s, name="", price=0, change_pct=0, change_amount=0, volume=0, amount=0, turnover=0, industry="") for s in symbols]

        try:
            quotes = self._market_provider.get_realtime_quotes(symbols=symbols, market=MarketCode.CN)
            quote_map = {str(q.code).zfill(6): q for q in quotes}
            # Also index by prefixed codes
            for q in quotes:
                code_str = str(q.code).zfill(6)
                quote_map[f"sh{code_str}"] = q
                quote_map[f"sz{code_str}"] = q
        except Exception as e:
            logger.error(f"Quote fetch failed: {e}")
            return [QuoteItem(code=s, name="", price=0, change_pct=0, change_amount=0, volume=0, amount=0, turnover=0, industry="") for s in symbols]

        codes_for_meta = [SymbolNormalizer.normalize_code(s).zfill(6) for s in symbols]
        meta_map = {}
        try:
            meta_map = get_stock_metadata_batch(codes_for_meta) or {}
        except Exception as e:
            logger.debug(f"Metadata lookup failed: {e}")

        for sym in symbols:
            sym_normalized = sym.lower().replace("sh", "").replace("sz", "").zfill(6)
            q = quote_map.get(sym) or quote_map.get(sym_normalized)
            industry = meta_map.get(sym_normalized, {}).get("industry", "") or getattr(q, 'industry', "") or "未分类"

            items.append(QuoteItem(
                code=sym,
                name=q.name if q else "",
                price=float(q.price) if q else 0.0,
                change_pct=float(q.change_pct) if q else 0.0,
                change_amount=float(q.change_amount) if q else 0.0,
                volume=int(q.volume) if q else 0,
                amount=float(q.amount) if q else 0.0,
                turnover=float(q.turnover) if q else 0.0,
                industry=industry,
            ))
        return items

    def _apply_sorting(self, items: list[QuoteItem], sort_by: SortBy, ascending: bool) -> None:
        reverse = not ascending
        if sort_by == SortBy.CHANGE_PCT:
            items.sort(key=lambda x: x.change_pct, reverse=reverse)
        elif sort_by == SortBy.PRICE:
            items.sort(key=lambda x: x.price, reverse=reverse)
        elif sort_by == SortBy.NAME:
            items.sort(key=lambda x: x.name, reverse=reverse)
        elif sort_by == SortBy.INDUSTRY:
            items.sort(key=lambda x: x.industry, reverse=reverse)

    def _apply_pagination(self, items: list[QuoteItem], page: int, page_size: int) -> WatchlistResponse:
        total = len(items)
        pages = (total + page_size - 1) // page_size
        start = (page - 1) * page_size
        return WatchlistResponse(
            items=items[start:start + page_size],
            total=total,
            page=page,
            page_size=page_size,
            pages=pages,
        )

    def add_price_alert(
        self,
        user_id: int,
        symbol: str,
        alert_type: str,
        threshold: float,
    ) -> tuple[bool, str]:
        if alert_type not in ("above", "below", "rise_pct", "fall_pct"):
            return False, "不支持的预警类型"
        if threshold <= 0:
            return False, "阈值必须大于 0"
        from app.domain.shared.symbol_normalizer import SymbolNormalizer
        normalized = SymbolNormalizer.to_db_code(symbol)
        if not normalized:
            return False, "股票代码不能为空"
        alert = {
            "symbol": normalized,
            "type": alert_type,
            "threshold": float(threshold),
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "triggered": False,
            "last_price": None,
            "last_change_pct": None,
            "triggered_at": None,
        }
        with self._price_alert_lock:
            user_key = str(user_id)
            self._price_alerts.setdefault(user_key, {})[self._alert_key(normalized, alert_type)] = alert
            self._write_price_alerts_locked()
        return True, "预警设置成功"

    def remove_price_alert(self, user_id: int, symbol: str, alert_type: str) -> tuple[bool, str]:
        from app.domain.shared.symbol_normalizer import SymbolNormalizer
        normalized = SymbolNormalizer.to_db_code(symbol)
        with self._price_alert_lock:
            user_alerts = self._price_alerts.get(str(user_id), {})
            removed = user_alerts.pop(self._alert_key(normalized, alert_type), None)
            if removed:
                self._write_price_alerts_locked()
        if not removed:
            return False, "预警不存在"
        return True, "预警已移除"

    def get_price_alerts(self, user_id: int) -> list[dict[str, Any]]:
        with self._price_alert_lock:
            alerts = list(self._price_alerts.get(str(user_id), {}).values())
        return sorted(alerts, key=lambda x: str(x.get("created_at") or ""), reverse=True)

    def check_price_alerts(self, user_id: int) -> list[dict[str, Any]]:
        alerts = self.get_price_alerts(user_id)
        if not alerts or not self._market_provider:
            return []
        symbols = sorted({str(a.get("symbol") or "").zfill(6) for a in alerts if a.get("symbol")})
        if not symbols:
            return []
        try:
            quotes = self._market_provider.get_realtime_quotes(symbols=symbols, market=MarketCode.CN)
        except Exception:
            return []
        quote_map = {str(q.code).zfill(6): q for q in quotes}
        triggered: list[dict[str, Any]] = []
        with self._price_alert_lock:
            user_alerts = self._price_alerts.setdefault(str(user_id), {})
            for alert in user_alerts.values():
                quote = quote_map.get(str(alert.get("symbol") or "").zfill(6))
                if not quote:
                    continue
                price = float(getattr(quote, "price", 0) or 0)
                change_pct = float(getattr(quote, "change_pct", 0) or 0)
                alert["last_price"] = price
                alert["last_change_pct"] = change_pct
                if self._is_alert_triggered(alert, price, change_pct):
                    alert["triggered"] = True
                    alert["triggered_at"] = alert.get("triggered_at") or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    triggered.append(dict(alert))
            self._write_price_alerts_locked()
        return triggered

    def _alert_key(self, symbol: str, alert_type: str) -> str:
        return f"{symbol}:{alert_type}"

    def _is_alert_triggered(self, alert: dict[str, Any], price: float, change_pct: float) -> bool:
        threshold = float(alert.get("threshold") or 0)
        alert_type = str(alert.get("type") or "")
        if alert_type == "above":
            return price >= threshold
        if alert_type == "below":
            return price <= threshold
        if alert_type == "rise_pct":
            return change_pct >= threshold
        if alert_type == "fall_pct":
            return change_pct <= -threshold
        return False

    def _read_price_alerts(self) -> GenericResponseDTO[str, dict[str, dict[str, Any]]]:
        if not self._price_alert_store_path or not self._price_alert_store_path.exists():
            return {}
        try:
            raw = json.loads(self._price_alert_store_path.read_text(encoding="utf-8"))
            if not isinstance(raw, dict):
                return {}
            return {
                str(uid): {str(key): dict(alert) for key, alert in dict(alerts or {}).items()}
                for uid, alerts in raw.items()
                if isinstance(alerts, dict)
            }
        except Exception:
            return {}

    def _write_price_alerts_locked(self) -> None:
        if not self._price_alert_store_path:
            return
        self._price_alert_store_path.write_text(
            json.dumps(self._price_alerts, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def export_to_blk(self, user_id: int, group_name: str | None = None) -> tuple[bool, str, str]:
        if group_name:
            if not self._stock_group_repository:
                return False, "分组服务未初始化", ""
            groups = self._stock_group_repository.list_groups(user_id=user_id)
            target = next((g for g in groups if g["name"] == group_name), None)
            if not target:
                return False, f"分组 {group_name} 不存在", ""
            symbols = self._stock_group_repository.list_group_symbols(target["id"], user_id=user_id)
        else:
            symbols = self._repository.list_symbols(user_id=user_id)
        blk_content = "\n".join(symbols)
        return True, f"导出 {len(symbols)} 只股票", blk_content

    def export_to_csv(self, user_id: int, group_name: str | None = None) -> tuple[bool, str, str]:
        if group_name:
            if not self._stock_group_repository:
                return False, "分组服务未初始化", ""
            groups = self._stock_group_repository.list_groups(user_id=user_id)
            target = next((g for g in groups if g["name"] == group_name), None)
            if not target:
                return False, f"分组 {group_name} 不存在", ""
            symbols = self._stock_group_repository.list_group_symbols(target["id"], user_id=user_id)
        else:
            symbols = self._repository.list_symbols(user_id=user_id)
        csv_lines = ["代码,市场"]
        for sym in symbols:
            market = "SH" if sym.startswith(("6", "5")) else "SZ"
            csv_lines.append(f"{sym},{market}")
        csv_content = "\n".join(csv_lines)
        return True, f"导出 {len(symbols)} 只股票", csv_content
