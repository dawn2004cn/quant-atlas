-- =====================================================
-- Quant Atlas MySQL 数据库建表脚本
-- =====================================================

-- 创建数据库
CREATE DATABASE IF NOT EXISTS quant_atlas CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE quant_atlas;

-- =====================================================
-- 用户权限相关表
-- =====================================================

CREATE TABLE IF NOT EXISTS roles (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(64) NOT NULL UNIQUE,
    can_manage_users BOOLEAN DEFAULT FALSE,
    can_manage_stocks BOOLEAN DEFAULT TRUE,
    can_run_backtest BOOLEAN DEFAULT TRUE,
    can_manage_agents BOOLEAN DEFAULT FALSE,
    permissions TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_role_name (name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(64) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    email VARCHAR(128),
    display_name VARCHAR(128),
    role_id INT,
    is_active BOOLEAN DEFAULT TRUE,
    last_login DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (role_id) REFERENCES roles(id) ON DELETE SET NULL,
    UNIQUE KEY uk_username (username)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =====================================================
-- 自选股相关表
-- =====================================================

CREATE TABLE IF NOT EXISTS watchlist (
    symbol VARCHAR(16) NOT NULL PRIMARY KEY,
    name VARCHAR(128) DEFAULT '',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS stock_groups (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(128) NOT NULL UNIQUE,
    description VARCHAR(512) DEFAULT '',
    is_default TINYINT DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_group_name (name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS stock_group_items (
    group_id INT NOT NULL,
    symbol VARCHAR(16) NOT NULL,
    added_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    is_removed TINYINT DEFAULT 0,
    PRIMARY KEY (group_id, symbol),
    FOREIGN KEY (group_id) REFERENCES stock_groups(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 插入默认分组
INSERT INTO stock_groups (name, description, is_default) VALUES ('默认分组', '系统默认自选股分组', 1)
ON DUPLICATE KEY UPDATE name = name;

-- =====================================================
-- 股票行情相关表
-- =====================================================

CREATE TABLE IF NOT EXISTS stocks (
    code VARCHAR(32) NOT NULL PRIMARY KEY,
    name VARCHAR(128) DEFAULT '',
    price DOUBLE DEFAULT 0,
    change_pct DOUBLE DEFAULT 0,
    change_amount DOUBLE DEFAULT 0,
    prev_close DOUBLE DEFAULT 0,
    volume DOUBLE DEFAULT 0,
    amount DOUBLE DEFAULT 0,
    turnover DOUBLE DEFAULT 0,
    volume_ratio DOUBLE DEFAULT 0,
    amplitude DOUBLE DEFAULT 0,
    pe DOUBLE DEFAULT 0,
    pb DOUBLE DEFAULT 0,
    total_market_cap DOUBLE DEFAULT 0,
    industry VARCHAR(128) DEFAULT '',
    update_time DATETIME,
    INDEX idx_industry (industry),
    INDEX idx_amount (amount),
    INDEX idx_volume (volume)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS stock_history (
    id INT AUTO_INCREMENT PRIMARY KEY,
    symbol VARCHAR(16) NOT NULL,
    date DATE NOT NULL,
    open DOUBLE,
    high DOUBLE,
    low DOUBLE,
    close DOUBLE,
    volume DOUBLE DEFAULT 0,
    amount DOUBLE DEFAULT 0,
    turnover DOUBLE DEFAULT 0,
    change_pct DOUBLE DEFAULT 0,
    change_amount DOUBLE DEFAULT 0,
    INDEX idx_symbol_date (symbol, date),
    UNIQUE KEY uk_symbol_date (symbol, date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS cn_stock_basics (
    code VARCHAR(16) NOT NULL PRIMARY KEY,
    name VARCHAR(128) NOT NULL,
    industry VARCHAR(128),
    market VARCHAR(32),
    list_date DATE,
    delist_date DATE,
    INDEX idx_industry (industry)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =====================================================
-- 板块相关表
-- =====================================================

CREATE TABLE IF NOT EXISTS tdx_blocks (
    id INT AUTO_INCREMENT PRIMARY KEY,
    code VARCHAR(16) NOT NULL UNIQUE,
    name VARCHAR(128) NOT NULL,
    type VARCHAR(32),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS tdx_block_items (
    block_id INT NOT NULL,
    symbol VARCHAR(16) NOT NULL,
    PRIMARY KEY (block_id, symbol),
    FOREIGN KEY (block_id) REFERENCES tdx_blocks(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =====================================================
-- 财务数据表
-- =====================================================

CREATE TABLE IF NOT EXISTS cn_finance_snapshots (
    id INT AUTO_INCREMENT PRIMARY KEY,
    symbol VARCHAR(16) NOT NULL,
    report_date DATE,
    report_type VARCHAR(32),
    total_assets DOUBLE,
    total_liabilities DOUBLE,
    total_revenue DOUBLE,
    net_profit DOUBLE,
    eps DOUBLE,
    roe DOUBLE,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_symbol_date (symbol, report_date),
    UNIQUE KEY uk_symbol_report (symbol, report_date, report_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS tdx_watchlists (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(128) NOT NULL,
    user_id INT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_user (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS tdx_watchlist_items (
    watchlist_id INT NOT NULL,
    symbol VARCHAR(16) NOT NULL,
    added_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (watchlist_id, symbol),
    FOREIGN KEY (watchlist_id) REFERENCES tdx_watchlists(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =====================================================
-- 市场情绪表
-- =====================================================

CREATE TABLE IF NOT EXISTS market_sentiment (
    id INT AUTO_INCREMENT PRIMARY KEY,
    market VARCHAR(16) NOT NULL,
    up_count INT DEFAULT 0,
    down_count INT DEFAULT 0,
    flat_count INT DEFAULT 0,
    total_count INT DEFAULT 0,
    sentiment_score DOUBLE,
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_market (market, update_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS market_sentiment_daily (
    id INT AUTO_INCREMENT PRIMARY KEY,
    market VARCHAR(16) NOT NULL,
    trade_date DATE NOT NULL,
    up_count INT DEFAULT 0,
    down_count INT DEFAULT 0,
    flat_count INT DEFAULT 0,
    sentiment_score DOUBLE,
    INDEX idx_market_date (market, trade_date),
    UNIQUE KEY uk_market_date (market, trade_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =====================================================
-- 龙虎榜数据表
-- =====================================================

CREATE TABLE IF NOT EXISTS longhu_daily (
    id INT AUTO_INCREMENT PRIMARY KEY,
    trade_date DATE NOT NULL,
    code VARCHAR(16) NOT NULL,
    name VARCHAR(128),
    reason VARCHAR(512),
    buy_amount DOUBLE DEFAULT 0,
    sell_amount DOUBLE DEFAULT 0,
    net_amount DOUBLE DEFAULT 0,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_date (trade_date),
    INDEX idx_code (code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =====================================================
-- 研报库表
-- =====================================================

CREATE TABLE IF NOT EXISTS yanbao_items (
    id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(512) NOT NULL,
    symbol VARCHAR(16),
    report_type VARCHAR(64),
    pub_date DATE,
    source VARCHAR(128),
    url VARCHAR(512),
    summary TEXT,
    entities TEXT,
    sentiment_score DOUBLE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_symbol (symbol),
    INDEX idx_date (pub_date),
    INDEX idx_type (report_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS archived_news (
    id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(512) NOT NULL,
    symbol VARCHAR(16),
    published_at DATETIME,
    source VARCHAR(128),
    url VARCHAR(512),
    summary TEXT,
    content TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_symbol (symbol),
    INDEX idx_published (published_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =====================================================
-- 信号池表
-- =====================================================

CREATE TABLE IF NOT EXISTS signal_flag_pool (
    id INT AUTO_INCREMENT PRIMARY KEY,
    symbol VARCHAR(16) NOT NULL,
    strategy_name VARCHAR(128) NOT NULL,
    signal_date DATE NOT NULL,
    signal_type VARCHAR(32),
    price DOUBLE,
    target_price DOUBLE,
    confidence_score DOUBLE,
    generated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_symbol (symbol),
    INDEX idx_date (signal_date),
    INDEX idx_strategy (strategy_name),
    UNIQUE KEY uk_symbol_strategy_date (symbol, strategy_name, signal_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =====================================================
-- FinGPT 表
-- =====================================================

CREATE TABLE IF NOT EXISTS fingpt_predictions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    ticker VARCHAR(32) NOT NULL,
    prediction_date DATE NOT NULL,
    source VARCHAR(32) DEFAULT 'unknown',
    source_ref VARCHAR(128),
    predicted_movement VARCHAR(64),
    positive_factors TEXT,
    potential_concerns TEXT,
    analysis_summary TEXT,
    confidence DOUBLE DEFAULT 0,
    actual_movement DOUBLE DEFAULT 0,
    is_correct INT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_ticker (ticker),
    INDEX idx_date (prediction_date),
    INDEX idx_created (created_at),
    UNIQUE KEY uk_ticker_date (ticker, prediction_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS fingpt_sentiment (
    id INT AUTO_INCREMENT PRIMARY KEY,
    ticker VARCHAR(32) NOT NULL,
    news_id VARCHAR(128),
    summary_hash VARCHAR(64) NOT NULL,
    source VARCHAR(32) DEFAULT 'unknown',
    source_ref VARCHAR(128),
    sentiment_score DOUBLE DEFAULT 0,
    key_entities VARCHAR(255),
    impact_level VARCHAR(32),
    summary TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_ticker (ticker),
    INDEX idx_created (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =====================================================
-- 投研数据表
-- =====================================================

CREATE TABLE IF NOT EXISTS analysis_reports (
    id INT AUTO_INCREMENT PRIMARY KEY,
    symbol VARCHAR(16),
    title VARCHAR(512) NOT NULL,
    content TEXT,
    analyst VARCHAR(64),
    report_date DATE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_symbol (symbol),
    INDEX idx_date (report_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS investment_managers (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(128) NOT NULL,
    code VARCHAR(32),
    type VARCHAR(32),
    established_date DATE,
    aum DOUBLE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_manager_code (code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS manager_nav (
    id INT AUTO_INCREMENT PRIMARY KEY,
    manager_id INT NOT NULL,
    trade_date DATE NOT NULL,
    nav DOUBLE NOT NULL,
    daily_return DOUBLE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (manager_id) REFERENCES investment_managers(id) ON DELETE CASCADE,
    INDEX idx_manager_date (manager_id, trade_date),
    UNIQUE KEY uk_manager_date (manager_id, trade_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS manager_trades (
    id INT AUTO_INCREMENT PRIMARY KEY,
    manager_id INT NOT NULL,
    trade_date DATE NOT NULL,
    symbol VARCHAR(16) NOT NULL,
    action VARCHAR(16),
    shares DOUBLE,
    price DOUBLE,
    amount DOUBLE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (manager_id) REFERENCES investment_managers(id) ON DELETE CASCADE,
    INDEX idx_manager_date (manager_id, trade_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =====================================================
-- Kronos 预测表
-- =====================================================

CREATE TABLE IF NOT EXISTS kronos_models (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(128) NOT NULL UNIQUE,
    model_type VARCHAR(64),
    description TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS kronos_predictions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    model_id INT NOT NULL,
    symbol VARCHAR(16) NOT NULL,
    prediction_date DATE NOT NULL,
    horizon_days INT,
    predicted_price DOUBLE,
    confidence DOUBLE,
    features TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (model_id) REFERENCES kronos_models(id) ON DELETE CASCADE,
    INDEX idx_symbol_date (symbol, prediction_date),
    INDEX idx_model (model_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =====================================================
-- 消息动态表
-- =====================================================

CREATE TABLE IF NOT EXISTS moments_posts (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    content TEXT NOT NULL,
    visibility VARCHAR(16) DEFAULT 'public',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_user (user_id),
    INDEX idx_created (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS moments_comments (
    id INT AUTO_INCREMENT PRIMARY KEY,
    post_id INT NOT NULL,
    user_id INT NOT NULL,
    content TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (post_id) REFERENCES moments_posts(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =====================================================
-- 交易通道表
-- =====================================================

CREATE TABLE IF NOT EXISTS ft_trades (
    id INT AUTO_INCREMENT PRIMARY KEY,
    symbol VARCHAR(16) NOT NULL,
    direction VARCHAR(8),
    open_price DOUBLE,
    close_price DOUBLE,
    pnl DOUBLE,
    status VARCHAR(16),
    opened_at DATETIME,
    closed_at DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_symbol (symbol),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS ft_orders (
    id INT AUTO_INCREMENT PRIMARY KEY,
    symbol VARCHAR(16) NOT NULL,
    direction VARCHAR(8),
    price DOUBLE,
    quantity DOUBLE,
    status VARCHAR(16),
    order_type VARCHAR(16),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_symbol (symbol)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =====================================================
-- 完成
-- =====================================================

SELECT '数据库创建完成!' AS status;