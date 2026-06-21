-- 为 stock_group_items 表添加 added_at 和 is_removed 字段
-- 执行: mysql -u root -p quant_atlas < scripts/migrations/stock_group_items_alter.sql

ALTER TABLE stock_group_items 
ADD COLUMN added_at DATETIME DEFAULT CURRENT_TIMESTAMP AFTER symbol;

ALTER TABLE stock_group_items 
ADD COLUMN is_removed TINYINT DEFAULT 0 AFTER added_at;

-- 回滚
-- ALTER TABLE stock_group_items DROP COLUMN is_removed;
-- ALTER TABLE stock_group_items DROP COLUMN added_at;