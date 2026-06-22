-- Initialize quant-atlas database schema
-- Run on MySQL container startup

CREATE DATABASE IF NOT EXISTS quant_atlas;
USE quant_atlas;

-- Market Data tables
CREATE TABLE IF NOT EXISTS market_quotes (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    symbol VARCHAR(32) NOT NULL,
    market VARCHAR(16) NOT NULL,
    timestamp DATETIME NOT NULL,
    open_price DECIMAL(18,4),
    high_price DECIMAL(18,4),
    low_price DECIMAL(18,4),
    close_price DECIMAL(18,4),
    volume BIGINT,
    amount DECIMAL(24,4),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_symbol_market (symbol, market, timestamp)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Strategy tables
CREATE TABLE IF NOT EXISTS strategy_templates (
    id VARCHAR(64) PRIMARY KEY,
    name VARCHAR(128) NOT NULL,
    category VARCHAR(32) NOT NULL,
    config JSON NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Portfolio tables
CREATE TABLE IF NOT EXISTS portfolio_positions (
    id VARCHAR(64) PRIMARY KEY,
    user_id VARCHAR(64) NOT NULL,
    symbol VARCHAR(32) NOT NULL,
    market VARCHAR(16) NOT NULL,
    quantity DECIMAL(18,4) NOT NULL,
    avg_cost DECIMAL(18,4) NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_user_id (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- AI Agent tables
CREATE TABLE IF NOT EXISTS ai_conversations (
    id VARCHAR(64) PRIMARY KEY,
    user_id VARCHAR(64) NOT NULL,
    messages JSON NOT NULL,
    context JSON,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_user_id (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- System/User tables
CREATE TABLE IF NOT EXISTS users (
    id VARCHAR(64) PRIMARY KEY,
    username VARCHAR(128) UNIQUE NOT NULL,
    email VARCHAR(256) UNIQUE NOT NULL,
    password_hash VARCHAR(256) NOT NULL,
    tier VARCHAR(32) DEFAULT 'free',
    preferences JSON,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Data Lake tables
CREATE TABLE IF NOT EXISTS data_sources (
    id VARCHAR(64) PRIMARY KEY,
    name VARCHAR(128) NOT NULL,
    type VARCHAR(32) NOT NULL,
    config JSON NOT NULL,
    status VARCHAR(16) DEFAULT 'active',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Research tables
CREATE TABLE IF NOT EXISTS research_reports (
    id VARCHAR(64) PRIMARY KEY,
    symbol VARCHAR(32) NOT NULL,
    market VARCHAR(16) NOT NULL,
    report_type VARCHAR(32) NOT NULL,
    content JSON NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_symbol_market (symbol, market)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Create service user
CREATE USER IF NOT EXISTS 'quant_service'@'%' IDENTIFIED BY 'quant_service_pass';
GRANT ALL PRIVILEGES ON quant_atlas.* TO 'quant_service'@'%';
FLUSH PRIVILEGES;
