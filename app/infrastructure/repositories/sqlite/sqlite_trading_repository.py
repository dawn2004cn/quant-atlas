"""SQLite implementation of TradeRepository."""

import sqlite3
from pathlib import Path

from app.domain.ports import TradeRepository
from app.domain.trading_entities import Order, Trade


class SQLiteTradingRepository(TradeRepository):
    """SQLite implementation of TradeRepository."""

    def __init__(self, db_path: Path | None = None) -> None:
        self._db_path = Path(db_path) if db_path else Path(".")
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self):
        conn = sqlite3.connect(str(self._db_path), timeout=30)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        return conn

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS ft_trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    exchange TEXT,
                    pair TEXT,
                    base_currency TEXT,
                    stake_currency TEXT,
                    is_open INTEGER DEFAULT 1,
                    open_date TEXT,
                    open_rate REAL,
                    open_rate_requested REAL,
                    close_date TEXT,
                    close_rate REAL,
                    close_rate_requested REAL,
                    close_profit REAL,
                    close_profit_abs REAL,
                    stake_amount REAL,
                    amount REAL,
                    stop_loss REAL,
                    stop_loss_pct REAL,
                    initial_stop_loss REAL,
                    initial_stop_loss_pct REAL,
                    is_stop_loss_trailing INTEGER DEFAULT 0,
                    max_rate REAL,
                    min_rate REAL,
                    exit_reason TEXT,
                    strategy TEXT,
                    enter_tag TEXT,
                    leverage REAL,
                    is_short INTEGER DEFAULT 0
                );
                CREATE TABLE IF NOT EXISTS ft_orders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ft_trade_id INTEGER,
                    order_id TEXT,
                    ft_pair TEXT,
                    ft_order_side TEXT,
                    ft_is_open INTEGER DEFAULT 1,
                    ft_amount REAL,
                    ft_price REAL,
                    status TEXT,
                    symbol TEXT,
                    order_type TEXT,
                    side TEXT,
                    filled REAL,
                    remaining REAL,
                    cost REAL,
                    order_date TEXT,
                    order_filled_date TEXT
                );
                """
            )
            conn.commit()

    def save_trade(self, trade: Trade) -> int:
        with self._connect() as conn:
            if trade.id is None:
                cur = conn.cursor()
                cur.execute(
                    """
                    INSERT INTO ft_trades (exchange, pair, base_currency, stake_currency, is_open, open_date, open_rate, open_rate_requested, stake_amount, amount, stop_loss, stop_loss_pct, initial_stop_loss, initial_stop_loss_pct, is_stop_loss_trailing, leverage, is_short, strategy, enter_tag)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        trade.exchange,
                        trade.pair,
                        trade.base_currency,
                        trade.stake_currency,
                        1 if trade.is_open else 0,
                        trade.open_date,
                        trade.open_rate,
                        trade.open_rate_requested,
                        trade.stake_amount,
                        trade.amount,
                        trade.stop_loss,
                        trade.stop_loss_pct,
                        trade.initial_stop_loss,
                        trade.initial_stop_loss_pct,
                        1 if trade.is_stop_loss_trailing else 0,
                        trade.leverage,
                        1 if trade.is_short else 0,
                        trade.strategy,
                        trade.enter_tag
                    )
                )
                conn.commit()
                trade.id = cur.lastrowid
            else:
                conn.execute(
                    """
                    UPDATE ft_trades SET
                        is_open = ?,
                        close_date = ?,
                        close_rate = ?,
                        close_rate_requested = ?,
                        close_profit = ?,
                        close_profit_abs = ?,
                        stop_loss = ?,
                        max_rate = ?,
                        min_rate = ?,
                        exit_reason = ?
                    WHERE id = ?
                    """,
                    (
                        1 if trade.is_open else 0,
                        trade.close_date,
                        trade.close_rate,
                        trade.close_rate_requested,
                        trade.close_profit,
                        trade.close_profit_abs,
                        trade.stop_loss,
                        trade.max_rate,
                        trade.min_rate,
                        trade.exit_reason,
                        trade.id
                    )
                )
                conn.commit()
            return trade.id

    def get_open_trades(self) -> list[Trade]:
        with self._connect() as conn:
            cur = conn.execute("SELECT * FROM ft_trades WHERE is_open = 1")
            rows = cur.fetchall()
            return [self._map_row_to_trade(r) for r in rows]

    def get_trade_by_id(self, trade_id: int) -> Trade | None:
        with self._connect() as conn:
            cur = conn.execute("SELECT * FROM ft_trades WHERE id = ?", (trade_id,))
            row = cur.fetchone()
            if not row:
                return None
            return self._map_row_to_trade(row)

    def save_order(self, order: Order) -> int:
        with self._connect() as conn:
            if order.id is None:
                cur = conn.cursor()
                cur.execute(
                    """
                    INSERT INTO ft_orders (ft_trade_id, order_id, ft_pair, ft_order_side, ft_is_open, ft_amount, ft_price, status, symbol, order_type, side, filled, remaining, cost, order_date, order_filled_date)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        order.ft_trade_id,
                        order.order_id,
                        order.ft_pair,
                        order.ft_order_side,
                        1 if order.ft_is_open else 0,
                        order.ft_amount,
                        order.ft_price,
                        order.status,
                        order.symbol,
                        order.order_type,
                        order.side,
                        order.filled,
                        order.remaining,
                        order.cost,
                        order.order_date,
                        order.order_filled_date
                    )
                )
                conn.commit()
                order.id = cur.lastrowid
            else:
                conn.execute(
                    """
                    UPDATE ft_orders SET
                        ft_is_open = ?,
                        status = ?,
                        filled = ?,
                        remaining = ?,
                        cost = ?,
                        order_filled_date = ?
                    WHERE id = ?
                    """,
                    (
                        1 if order.ft_is_open else 0,
                        order.status,
                        order.filled,
                        order.remaining,
                        order.cost,
                        order.order_filled_date,
                        order.id
                    )
                )
                conn.commit()
            return order.id

    def _map_row_to_trade(self, row) -> Trade:
        return Trade(
            id=row["id"],
            exchange=row["exchange"],
            pair=row["pair"],
            base_currency=row["base_currency"],
            stake_currency=row["stake_currency"],
            is_open=bool(row["is_open"]),
            open_date=row["open_date"],
            open_rate=row["open_rate"],
            open_rate_requested=row["open_rate_requested"],
            close_date=row["close_date"],
            close_rate=row["close_rate"],
            close_rate_requested=row["close_rate_requested"],
            close_profit=row["close_profit"],
            close_profit_abs=row["close_profit_abs"],
            stake_amount=row["stake_amount"],
            amount=row["amount"],
            stop_loss=row["stop_loss"],
            stop_loss_pct=row["stop_loss_pct"],
            initial_stop_loss=row["initial_stop_loss"],
            initial_stop_loss_pct=row["initial_stop_loss_pct"],
            is_stop_loss_trailing=bool(row["is_stop_loss_trailing"]),
            max_rate=row["max_rate"],
            min_rate=row["min_rate"],
            exit_reason=row["exit_reason"],
            strategy=row["strategy"],
            enter_tag=row["enter_tag"],
            leverage=row["leverage"],
            is_short=bool(row["is_short"]),
        )
