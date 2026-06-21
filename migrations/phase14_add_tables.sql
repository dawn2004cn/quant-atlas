-- Phase 14: 零售赋能与无代码量化实验室
-- Creates tables for Wisdom Mesh, Trading DNA/XP, and crowd-voting.

CREATE TABLE IF NOT EXISTS shared_strategies (
    id           VARCHAR(36) PRIMARY KEY,
    anonymized_id VARCHAR(36) NOT NULL UNIQUE,
    strategy_name VARCHAR(255),
    strategy_spec JSON NOT NULL,
    performance_summary JSON,
    success_score FLOAT,
    contributor_tier VARCHAR(20) DEFAULT 'observe',
    factor_config JSON,
    vote_count   INT DEFAULT 0,
    vote_for     INT DEFAULT 0,
    vote_against INT DEFAULT 0,
    created_at   DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at   DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_tier (contributor_tier),
    INDEX idx_success (success_score),
    INDEX idx_created (created_at)
);

CREATE TABLE IF NOT EXISTS user_trading_dna (
    user_id                VARCHAR(36) PRIMARY KEY,
    total_xp               INT DEFAULT 0,
    prudent_actions        INT DEFAULT 0,
    reckless_actions       INT DEFAULT 0,
    streak_days            INT DEFAULT 0,
    risk_companion_msgs    INT DEFAULT 0,
    created_at             DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at             DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS user_xp_events (
    id         BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id    VARCHAR(36) NOT NULL,
    event_type VARCHAR(50) NOT NULL,
    points     INT NOT NULL,
    context    TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_user (user_id),
    INDEX idx_event (event_type),
    INDEX idx_created (created_at)
);

CREATE TABLE IF NOT EXISTS wisdom_votes (
    id             BIGINT AUTO_INCREMENT PRIMARY KEY,
    strategy_id    VARCHAR(36) NOT NULL,
    voter_id       VARCHAR(36) NOT NULL,
    factor_name    VARCHAR(100),
    original_weight FLOAT,
    proposed_weight FLOAT,
    vote_type      VARCHAR(50),
    rationale      TEXT,
    votes_for      INT DEFAULT 0,
    votes_against  INT DEFAULT 0,
    created_at     DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_strategy (strategy_id),
    INDEX idx_voter (voter_id),
    INDEX idx_created (created_at)
);
