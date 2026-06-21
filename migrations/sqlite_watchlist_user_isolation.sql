-- =====================================================
-- SQLite 版本自选股用户隔离迁移脚本
-- 执行日期: 2024-04-30
-- =====================================================

-- 1. 为 stock_groups 表添加 user_id 列
ALTER TABLE stock_groups ADD COLUMN user_id INTEGER NOT NULL DEFAULT 1;

-- 2. 为 stock_group_items 表添加 user_id 列
ALTER TABLE stock_group_items ADD COLUMN user_id INTEGER NOT NULL DEFAULT 1;

-- 3. 创建索引以提高查询性能
CREATE INDEX IF NOT EXISTS ix_stock_groups_user_id ON stock_groups(user_id);
CREATE INDEX IF NOT EXISTS ix_stock_group_items_user_id ON stock_group_items(user_id);
CREATE UNIQUE INDEX IF NOT EXISTS ix_stock_groups_user_id_name ON stock_groups(user_id, name);

-- =====================================================
-- 回滚脚本 (如需回滚)
-- =====================================================
-- DROP INDEX IF EXISTS ix_stock_groups_user_id_name ON stock_groups;
-- DROP INDEX IF EXISTS ix_stock_group_items_user_id ON stock_group_items;
-- DROP INDEX IF EXISTS ix_stock_groups_user_id ON stock_groups;
-- -- 注意: SQLite 不支持 DROP COLUMN，需要重建表
-- -- 如需回滚，建议备份数据后重建表