-- =====================================================
-- 自选股用户隔离数据库迁移脚本
-- 执行日期: 2024-04-30
-- =====================================================

-- =====================================================
-- MySQL 版本
-- =====================================================

-- 1. 为 stock_groups 表添加 user_id 列
ALTER TABLE stock_groups ADD COLUMN user_id INT NOT NULL DEFAULT 1;

-- 2. 为 stock_group_items 表添加 user_id 列
ALTER TABLE stock_group_items ADD COLUMN user_id INT NOT NULL DEFAULT 1;

-- 3. 创建索引以提高查询性能
CREATE INDEX ix_stock_groups_user_id ON stock_groups(user_id);
CREATE INDEX ix_stock_group_items_user_id ON stock_group_items(user_id);
CREATE UNIQUE INDEX ix_stock_groups_user_id_name ON stock_groups(user_id, name);

-- =====================================================
-- 回滚脚本 (如需回滚)
-- =====================================================
-- DROP INDEX ix_stock_groups_user_id_name ON stock_groups;
-- DROP INDEX ix_stock_group_items_user_id ON stock_group_items;
-- DROP INDEX ix_stock_groups_user_id ON stock_groups;
-- ALTER TABLE stock_group_items DROP COLUMN user_id;
-- ALTER TABLE stock_groups DROP COLUMN user_id;