-- Migration: Add source_ref column to fingpt_predictions and fingpt_sentiment tables
-- Run this SQL against your MySQL database

-- 1. Add source_ref to fingpt_predictions
ALTER TABLE fingpt_predictions ADD COLUMN source_ref VARCHAR(128) DEFAULT NULL;

-- 2. Add source_ref to fingpt_sentiment
ALTER TABLE fingpt_sentiment ADD COLUMN source_ref VARCHAR(128) DEFAULT NULL;

-- 3. Verify columns were added
DESCRIBE fingpt_predictions;
DESCRIBE fingpt_sentiment;