from __future__ import annotations

"""Portfolio trade record service - manage transaction history and calculate holdings."""


import json
from datetime import date, datetime
from pathlib import Path
from typing import Any

from app.application.dto.portfolio_dto import PortfolioPerformanceDTO, TradeRecordDTO
from app.core.base_service import BaseApplicationService
from app.domain.enums import MarketCode
from app.domain.ports import IMarketDataProvider

DATA_DIR = Path(__file__).parent.parent.parent / "data" / "portfolio"
DATA_DIR.mkdir(parents=True, exist_ok=True)

_MARKET_FETCH_ERRORS = (
    OSError,
    RuntimeError,
    ValueError,
    TypeError,
    AttributeError,
    ConnectionError,
    TimeoutError,
)


def _get_user_file(user_id: int) -> Path:
    return DATA_DIR / f"trades_{user_id}.json"


class PortfolioTradeService(BaseApplicationService):
    """Service for managing trade records and calculating portfolio metrics."""

    def __init__(self, market_provider: IMarketDataProvider | None = None):
        super().__init__()
        if market_provider is not None:
            self._market = market_provider
        else:
            from app.modules.system.services.helpers.service_resolver_access import resolve_optional_service
            self._market = resolve_optional_service(IMarketDataProvider)
        if self._market is None:
            from app.modules.system.services.helpers.market_data_provider import get_market_data_provider

            self._market = get_market_data_provider()

    def save_trade(self, user_id: int, trade: TradeRecordDTO) -> int:
        """Save a single trade record."""
        trades = self._load_trades(user_id)
        trade.id = len(trades) + 1
        trades.append(trade.model_dump(mode='json'))
        self._save_trades(user_id, trades)
        return trade.id

    def import_trades(self, user_id: int, trades: list[TradeRecordDTO]) -> int:
        """Import multiple trade records."""
        existing = self._load_trades(user_id)
        start_id = len(existing) + 1
        for i, t in enumerate(trades):
            t.id = start_id + i
            existing.append(t.model_dump(mode='json'))
        self._save_trades(user_id, existing)
        return len(trades)

    def list_trades(self, user_id: int, start_date: date | None = None, end_date: date | None = None) -> list[TradeRecordDTO]:
        """List all trade records for a user, optionally filtered by date range."""
        trades = self._load_trades(user_id)
        result = []
        for t in trades:
            td = t.get('trade_date')
            if isinstance(td, str):
                td = datetime.fromisoformat(td).date()
            elif isinstance(td, date):
                td = td
            else:
                continue
            if start_date and td < start_date:
                continue
            if end_date and td > end_date:
                continue
            result.append(TradeRecordDTO(**t))
        return result

    def calculate_holdings(self, user_id: int, as_of_date: date | None = None) -> list[dict[str, Any]]:
        """Calculate current holdings from trade history."""
        trades = self._load_trades(user_id)
        if as_of_date:
            trades = [t for t in trades if datetime.fromisoformat(t['trade_date']).date() <= as_of_date]

        holdings: dict[str, dict] = {}
        for t in trades:
            sym = t['symbol']
            if sym not in holdings:
                holdings[sym] = {'shares': 0, 'cost': 0.0}
            qty = t['quantity']
            price = t['price']
            if t['direction'] == 'BUY':
                holdings[sym]['shares'] += qty
                holdings[sym]['cost'] += qty * price + t.get('fee', 0)
            elif t['direction'] == 'SELL':
                holdings[sym]['shares'] -= qty
                sell_ratio = qty / (holdings[sym]['shares'] + qty) if holdings[sym]['shares'] + qty > 0 else 0
                holdings[sym]['cost'] *= (1 - sell_ratio)

        result = []
        symbols = list(holdings.keys())
        if symbols:
            try:
                quotes = self._market.get_realtime_quotes(symbols, market=MarketCode.CN)
                price_map = {q.code: q.price for q in quotes}
                name_map = {q.code: q.name for q in quotes}
            except _MARKET_FETCH_ERRORS:
                price_map = {s: 0.0 for s in symbols}
                name_map = {s: s for s in symbols}

            for sym, h in holdings.items():
                if h['shares'] <= 0:
                    continue
                current_price = price_map.get(sym, 0)
                current_value = h['shares'] * current_price
                avg_cost = h['cost'] / h['shares'] if h['shares'] > 0 else 0
                pnl = current_value - h['cost']
                pnl_pct = (pnl / h['cost'] * 100) if h['cost'] > 0 else 0
                result.append({
                    'code': sym,
                    'name': name_map.get(sym, sym),
                    'shares': h['shares'],
                    'cost': round(h['cost'], 2),
                    'avg_cost': round(avg_cost, 2),
                    'price': current_price,
                    'value': round(current_value, 2),
                    'pnl': round(pnl, 2),
                    'pnl_pct': round(pnl_pct, 2),
                })

        return sorted(result, key=lambda x: -x['value'])

    def calculate_performance(self, user_id: int, start_date: date, end_date: date) -> list[PortfolioPerformanceDTO]:
        """Calculate daily performance from trade history."""
        trades = self._load_trades(user_id)
        trade_dates = sorted(set(datetime.fromisoformat(t['trade_date']).date() for t in trades if start_date <= datetime.fromisoformat(t['trade_date']).date() <= end_date))

        if not trade_dates:
            return []

        holdings_before = {}
        cumulative_cost = 0.0
        results = []

        for d in trade_dates:
            daily_trades = [t for t in trades if datetime.fromisoformat(t['trade_date']).date() == d]

            sum(t['quantity'] * t['price'] + t.get('fee', 0) for t in daily_trades if t['direction'] == 'BUY')
            sum(t['quantity'] * t['price'] - t.get('fee', 0) for t in daily_trades if t['direction'] == 'SELL')

            for t in daily_trades:
                sym = t['symbol']
                if sym not in holdings_before:
                    holdings_before[sym] = {'shares': 0, 'cost': 0.0}
                qty = t['quantity']
                price = t['price']
                if t['direction'] == 'BUY':
                    holdings_before[sym]['shares'] += qty
                    holdings_before[sym]['cost'] += qty * price + t.get('fee', 0)
                elif t['direction'] == 'SELL':
                    holdings_before[sym]['shares'] -= qty

            symbols = [s for s, h in holdings_before.items() if h['shares'] > 0]
            current_value = 0.0
            if symbols:
                try:
                    quotes = self._market.get_realtime_quotes(symbols, market=MarketCode.CN)
                    price_map = {q.code: q.price for q in quotes}
                except _MARKET_FETCH_ERRORS:
                    price_map = {}
                for sym, h in holdings_before.items():
                    if h['shares'] > 0:
                        current_value += h['shares'] * price_map.get(sym, 0)

            prev_value = results[-1].total_value if results else 100000.0
            daily_return = (current_value - prev_value) / prev_value * 100 if prev_value > 0 else 0
            daily_pnl = current_value - prev_value

            cumulative_cost = sum(h['cost'] for h in holdings_before.values())
            cumulative_return = (current_value - cumulative_cost) / cumulative_cost * 100 if cumulative_cost > 0 else 0

            results.append(PortfolioPerformanceDTO(
                date=d,
                total_value=round(current_value, 2),
                daily_return=round(daily_return, 2),
                daily_pnl=round(daily_pnl, 2),
                cumulative_return=round(cumulative_return, 2),
                cumulative_pnl=round(current_value - cumulative_cost, 2),
            ))

        return results

    def _load_trades(self, user_id: int) -> list[dict]:
        """Load trades from JSON file."""
        f = _get_user_file(user_id)
        if not f.exists():
            return []
        try:
            with open(f, encoding='utf-8') as fp:
                return json.load(fp)
        except (OSError, json.JSONDecodeError, TypeError, ValueError) as e:
            self.logger.error("Error loading trades: %s", e)
            return []

    def _save_trades(self, user_id: int, trades: list[dict]) -> None:
        """Save trades to JSON file."""
        f = _get_user_file(user_id)
        try:
            with open(f, 'w', encoding='utf-8') as fp:
                json.dump(trades, fp, ensure_ascii=False, indent=2, default=str)
        except OSError as e:
            self.logger.error("Error saving trades: %s", e)
