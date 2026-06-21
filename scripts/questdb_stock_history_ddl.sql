-- QuestDB OHLCV（与 ILP 写入字段一致，表名对应 QUESTDB_OHLCV_TABLE）
CREATE TABLE IF NOT EXISTS stock_history (
    stock_code SYMBOL,
    trade_date DATE,
    open DOUBLE,
    high DOUBLE,
    low DOUBLE,
    close DOUBLE,
    volume DOUBLE,
    amount DOUBLE
) timestamp(trade_date) PARTITION BY DAY WAL
DEDUP UPSERT KEYS(trade_date, stock_code);
