"""复权因子表创建脚本."""

CREATE_ADJUSTMENT_FACTOR_TABLE = """
CREATE TABLE IF NOT EXISTS stock_adjustment_factor (
    stock_code VARCHAR(20) NOT NULL,
    date DATE NOT NULL,
    factor DECIMAL(10, 6) NOT NULL DEFAULT 1.000000,
    PRIMARY KEY (stock_code, date),
    INDEX idx_stock_code (stock_code),
    INDEX idx_date (date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='股票复权因子表 - 用于前后复权计算';
"""

# SQLite 版本
CREATE_ADJUSTMENT_FACTOR_TABLE_SQLITE = """
CREATE TABLE IF NOT EXISTS stock_adjustment_factor (
    stock_code TEXT NOT NULL,
    date TEXT NOT NULL,
    factor REAL NOT NULL DEFAULT 1.0,
    PRIMARY KEY (stock_code, date)
);

CREATE INDEX IF NOT EXISTS idx_factor_stock ON stock_adjustment_factor(stock_code);
CREATE INDEX IF NOT EXISTS idx_factor_date ON stock_adjustment_factor(date);
"""
