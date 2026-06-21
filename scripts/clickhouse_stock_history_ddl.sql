-- ClickHouse OHLCV (align with QuestDB stock_history + app CLICKHOUSE_OHLCV_TABLE)
-- ReplacingMergeTree: 同 (stock_code, trade_date) 重复 INSERT 后台合并去重
CREATE TABLE IF NOT EXISTS stock_history
(
    stock_code String,
    trade_date Date,
    open Float64,
    high Float64,
    low Float64,
    close Float64,
    volume Float64,
    amount Float64
)
ENGINE = ReplacingMergeTree
ORDER BY (stock_code, trade_date);
