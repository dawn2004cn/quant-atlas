-- 热点板块（东财概念/行业涨幅榜）MySQL 表
-- 应用启动时亦可通过 SQLAlchemy create_all 创建；本脚本便于手工初始化

CREATE TABLE IF NOT EXISTS em_hot_sector_snapshots (
    snapshot_at VARCHAR(32) NOT NULL PRIMARY KEY,
    trade_date VARCHAR(10) NOT NULL,
    ingest_kind VARCHAR(16) NOT NULL,
    sector_count INT NOT NULL DEFAULT 0,
    member_rows INT NOT NULL DEFAULT 0,
    source VARCHAR(32) NOT NULL DEFAULT 'eastmoney',
    INDEX idx_em_hot_snap_trade_date (trade_date),
    INDEX idx_em_hot_snap_kind (ingest_kind)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS em_hot_sectors (
    snapshot_at VARCHAR(32) NOT NULL,
    sector_code VARCHAR(16) NOT NULL,
    name VARCHAR(128) NOT NULL,
    kind VARCHAR(16) NOT NULL,
    source VARCHAR(64) NOT NULL,
    change_pct DOUBLE NOT NULL DEFAULT 0,
    price DOUBLE NOT NULL DEFAULT 0,
    amount DOUBLE NOT NULL DEFAULT 0,
    volume DOUBLE NOT NULL DEFAULT 0,
    turnover_rate DOUBLE NOT NULL DEFAULT 0,
    rank_no INT NOT NULL DEFAULT 0,
    PRIMARY KEY (snapshot_at, sector_code),
    INDEX idx_em_hot_sectors_name (name),
    INDEX idx_em_hot_sectors_kind (kind),
    INDEX idx_em_hot_sectors_chg (change_pct)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS em_hot_sector_members (
    snapshot_at VARCHAR(32) NOT NULL,
    sector_code VARCHAR(16) NOT NULL,
    symbol VARCHAR(16) NOT NULL,
    name VARCHAR(128) NOT NULL DEFAULT '',
    change_pct DOUBLE NOT NULL DEFAULT 0,
    price DOUBLE NOT NULL DEFAULT 0,
    amount DOUBLE NOT NULL DEFAULT 0,
    volume DOUBLE NOT NULL DEFAULT 0,
    PRIMARY KEY (snapshot_at, sector_code, symbol),
    INDEX idx_em_hot_members_symbol (symbol)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
