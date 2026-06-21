-- =====================================================
-- 统一 A 股股票代码为 sh600519 格式
-- 执行前请备份数据库！
-- =====================================================

-- 处理 CN: 前缀
UPDATE watchlist SET symbol = SUBSTRING(symbol, 4) WHERE symbol LIKE 'CN:%' OR symbol LIKE 'cn:%';
UPDATE stock_group_items SET symbol = SUBSTRING(symbol, 4) WHERE symbol LIKE 'CN:%' OR symbol LIKE 'cn:%';
UPDATE tdx_block_items SET symbol = SUBSTRING(symbol, 4) WHERE symbol LIKE 'CN:%' OR symbol LIKE 'cn:%';
UPDATE tdx_watchlist_items SET symbol = SUBSTRING(symbol, 4) WHERE symbol LIKE 'CN:%' OR symbol LIKE 'cn:%';
UPDATE stocks SET code = SUBSTRING(code, 4) WHERE code LIKE 'CN:%' OR code LIKE 'cn:%';
UPDATE cn_stock_basics SET symbol = SUBSTRING(symbol, 4) WHERE symbol LIKE 'CN:%' OR symbol LIKE 'cn:%';
UPDATE stock_history SET stock_code = SUBSTRING(stock_code, 4) WHERE stock_code LIKE 'CN:%' OR stock_code LIKE 'cn:%';
UPDATE stock_history_sh SET stock_code = SUBSTRING(stock_code, 4) WHERE stock_code LIKE 'CN:%' OR stock_code LIKE 'cn:%';
UPDATE stock_history_sz SET stock_code = SUBSTRING(stock_code, 4) WHERE stock_code LIKE 'CN:%' OR stock_code LIKE 'cn:%';
UPDATE stock_history_bj SET stock_code = SUBSTRING(stock_code, 4) WHERE stock_code LIKE 'CN:%' OR stock_code LIKE 'cn:%';
UPDATE cn_finance_snapshots SET symbol = SUBSTRING(symbol, 4) WHERE symbol LIKE 'CN:%' OR symbol LIKE 'cn:%';
UPDATE yanbao_items SET stock_code = SUBSTRING(stock_code, 4) WHERE stock_code LIKE 'CN:%' OR stock_code LIKE 'cn:%';
UPDATE archived_news SET symbol = SUBSTRING(symbol, 4) WHERE symbol LIKE 'CN:%' OR symbol LIKE 'cn:%';
UPDATE news_symbol_meta SET symbol = SUBSTRING(symbol, 4) WHERE symbol LIKE 'CN:%' OR symbol LIKE 'cn:%';
UPDATE signal_flag_pool SET code = SUBSTRING(code, 4) WHERE code LIKE 'CN:%' OR code LIKE 'cn:%';
UPDATE fingpt_predictions SET ticker = SUBSTRING(ticker, 4) WHERE ticker LIKE 'CN:%' OR ticker LIKE 'cn:%';
UPDATE fingpt_sentiment SET ticker = SUBSTRING(ticker, 4) WHERE ticker LIKE 'CN:%' OR ticker LIKE 'cn:%';
UPDATE kronos_predictions SET symbol = SUBSTRING(symbol, 4) WHERE symbol LIKE 'CN:%' OR symbol LIKE 'cn:%';
UPDATE analysis_reports SET symbol = SUBSTRING(symbol, 4) WHERE symbol LIKE 'CN:%' OR symbol LIKE 'cn:%';
UPDATE manager_trades SET symbol = SUBSTRING(symbol, 4) WHERE symbol LIKE 'CN:%' OR symbol LIKE 'cn:%';
UPDATE manager_positions_state SET symbol = SUBSTRING(symbol, 4) WHERE symbol LIKE 'CN:%' OR symbol LIKE 'cn:%';
UPDATE manager_holdings_snap SET symbol = SUBSTRING(symbol, 4) WHERE symbol LIKE 'CN:%' OR symbol LIKE 'cn:%';
UPDATE longhu_daily SET code = SUBSTRING(code, 4) WHERE code LIKE 'CN:%' OR code LIKE 'cn:%';
UPDATE ai_trading_records SET symbol = SUBSTRING(symbol, 4) WHERE symbol LIKE 'CN:%' OR symbol LIKE 'cn:%';
UPDATE ai_committee_selection_trades SET symbol = SUBSTRING(symbol, 4) WHERE symbol LIKE 'CN:%' OR symbol LIKE 'cn:%';
UPDATE em_hot_sector_members SET symbol = SUBSTRING(symbol, 4) WHERE symbol LIKE 'CN:%' OR symbol LIKE 'cn:%';
UPDATE user_race_trades SET symbol = SUBSTRING(symbol, 4) WHERE symbol LIKE 'CN:%' OR symbol LIKE 'cn:%';
UPDATE execution_records SET symbol = SUBSTRING(symbol, 4) WHERE symbol LIKE 'CN:%' OR symbol LIKE 'cn:%';

-- 处理纯 6 位数字 -> 添加市场前缀
-- 6xxxxx -> sh
UPDATE watchlist SET symbol = CONCAT('sh', symbol) WHERE symbol REGEXP '^6[0-9]{5}$';
UPDATE stock_group_items SET symbol = CONCAT('sh', symbol) WHERE symbol REGEXP '^6[0-9]{5}$';
UPDATE tdx_block_items SET symbol = CONCAT('sh', symbol) WHERE symbol REGEXP '^6[0-9]{5}$';
UPDATE tdx_watchlist_items SET symbol = CONCAT('sh', symbol) WHERE symbol REGEXP '^6[0-9]{5}$';
UPDATE stocks SET code = CONCAT('sh', code) WHERE code REGEXP '^6[0-9]{5}$';
UPDATE cn_stock_basics SET symbol = CONCAT('sh', symbol) WHERE symbol REGEXP '^6[0-9]{5}$';
UPDATE stock_history SET stock_code = CONCAT('sh', stock_code) WHERE stock_code REGEXP '^6[0-9]{5}$';
UPDATE stock_history_sh SET stock_code = CONCAT('sh', stock_code) WHERE stock_code REGEXP '^6[0-9]{5}$';
UPDATE stock_history_sz SET stock_code = CONCAT('sh', stock_code) WHERE stock_code REGEXP '^6[0-9]{5}$';
UPDATE stock_history_bj SET stock_code = CONCAT('sh', stock_code) WHERE stock_code REGEXP '^6[0-9]{5}$';
UPDATE cn_finance_snapshots SET symbol = CONCAT('sh', symbol) WHERE symbol REGEXP '^6[0-9]{5}$';
UPDATE yanbao_items SET stock_code = CONCAT('sh', stock_code) WHERE stock_code REGEXP '^6[0-9]{5}$';
UPDATE archived_news SET symbol = CONCAT('sh', symbol) WHERE symbol REGEXP '^6[0-9]{5}$';
UPDATE news_symbol_meta SET symbol = CONCAT('sh', symbol) WHERE symbol REGEXP '^6[0-9]{5}$';
UPDATE signal_flag_pool SET code = CONCAT('sh', code) WHERE code REGEXP '^6[0-9]{5}$';
UPDATE fingpt_predictions SET ticker = CONCAT('sh', ticker) WHERE ticker REGEXP '^6[0-9]{5}$';
UPDATE fingpt_sentiment SET ticker = CONCAT('sh', ticker) WHERE ticker REGEXP '^6[0-9]{5}$';
UPDATE kronos_predictions SET symbol = CONCAT('sh', symbol) WHERE symbol REGEXP '^6[0-9]{5}$';
UPDATE analysis_reports SET symbol = CONCAT('sh', symbol) WHERE symbol REGEXP '^6[0-9]{5}$';
UPDATE manager_trades SET symbol = CONCAT('sh', symbol) WHERE symbol REGEXP '^6[0-9]{5}$';
UPDATE manager_positions_state SET symbol = CONCAT('sh', symbol) WHERE symbol REGEXP '^6[0-9]{5}$';
UPDATE manager_holdings_snap SET symbol = CONCAT('sh', symbol) WHERE symbol REGEXP '^6[0-9]{5}$';
UPDATE longhu_daily SET code = CONCAT('sh', code) WHERE code REGEXP '^6[0-9]{5}$';
UPDATE ai_trading_records SET symbol = CONCAT('sh', symbol) WHERE symbol REGEXP '^6[0-9]{5}$';
UPDATE ai_committee_selection_trades SET symbol = CONCAT('sh', symbol) WHERE symbol REGEXP '^6[0-9]{5}$';
UPDATE em_hot_sector_members SET symbol = CONCAT('sh', symbol) WHERE symbol REGEXP '^6[0-9]{5}$';
UPDATE user_race_trades SET symbol = CONCAT('sh', symbol) WHERE symbol REGEXP '^6[0-9]{5}$';
UPDATE execution_records SET symbol = CONCAT('sh', symbol) WHERE symbol REGEXP '^6[0-9]{5}$';

-- 0xxxxx, 3xxxxx -> sz
UPDATE watchlist SET symbol = CONCAT('sz', symbol) WHERE symbol REGEXP '^[03][0-9]{5}$';
UPDATE stock_group_items SET symbol = CONCAT('sz', symbol) WHERE symbol REGEXP '^[03][0-9]{5}$';
UPDATE tdx_block_items SET symbol = CONCAT('sz', symbol) WHERE symbol REGEXP '^[03][0-9]{5}$';
UPDATE tdx_watchlist_items SET symbol = CONCAT('sz', symbol) WHERE symbol REGEXP '^[03][0-9]{5}$';
UPDATE stocks SET code = CONCAT('sz', code) WHERE code REGEXP '^[03][0-9]{5}$';
UPDATE cn_stock_basics SET symbol = CONCAT('sz', symbol) WHERE symbol REGEXP '^[03][0-9]{5}$';
UPDATE stock_history SET stock_code = CONCAT('sz', stock_code) WHERE stock_code REGEXP '^[03][0-9]{5}$';
UPDATE stock_history_sh SET stock_code = CONCAT('sz', stock_code) WHERE stock_code REGEXP '^[03][0-9]{5}$';
UPDATE stock_history_sz SET stock_code = CONCAT('sz', stock_code) WHERE stock_code REGEXP '^[03][0-9]{5}$';
UPDATE stock_history_bj SET stock_code = CONCAT('sz', stock_code) WHERE stock_code REGEXP '^[03][0-9]{5}$';
UPDATE cn_finance_snapshots SET symbol = CONCAT('sz', symbol) WHERE symbol REGEXP '^[03][0-9]{5}$';
UPDATE yanbao_items SET stock_code = CONCAT('sz', stock_code) WHERE stock_code REGEXP '^[03][0-9]{5}$';
UPDATE archived_news SET symbol = CONCAT('sz', symbol) WHERE symbol REGEXP '^[03][0-9]{5}$';
UPDATE news_symbol_meta SET symbol = CONCAT('sz', symbol) WHERE symbol REGEXP '^[03][0-9]{5}$';
UPDATE signal_flag_pool SET code = CONCAT('sz', code) WHERE code REGEXP '^[03][0-9]{5}$';
UPDATE fingpt_predictions SET ticker = CONCAT('sz', ticker) WHERE ticker REGEXP '^[03][0-9]{5}$';
UPDATE fingpt_sentiment SET ticker = CONCAT('sz', ticker) WHERE ticker REGEXP '^[03][0-9]{5}$';
UPDATE kronos_predictions SET symbol = CONCAT('sz', symbol) WHERE symbol REGEXP '^[03][0-9]{5}$';
UPDATE analysis_reports SET symbol = CONCAT('sz', symbol) WHERE symbol REGEXP '^[03][0-9]{5}$';
UPDATE manager_trades SET symbol = CONCAT('sz', symbol) WHERE symbol REGEXP '^[03][0-9]{5}$';
UPDATE manager_positions_state SET symbol = CONCAT('sz', symbol) WHERE symbol REGEXP '^[03][0-9]{5}$';
UPDATE manager_holdings_snap SET symbol = CONCAT('sz', symbol) WHERE symbol REGEXP '^[03][0-9]{5}$';
UPDATE longhu_daily SET code = CONCAT('sz', code) WHERE code REGEXP '^[03][0-9]{5}$';
UPDATE ai_trading_records SET symbol = CONCAT('sz', symbol) WHERE symbol REGEXP '^[03][0-9]{5}$';
UPDATE ai_committee_selection_trades SET symbol = CONCAT('sz', symbol) WHERE symbol REGEXP '^[03][0-9]{5}$';
UPDATE em_hot_sector_members SET symbol = CONCAT('sz', symbol) WHERE symbol REGEXP '^[03][0-9]{5}$';
UPDATE user_race_trades SET symbol = CONCAT('sz', symbol) WHERE symbol REGEXP '^[03][0-9]{5}$';
UPDATE execution_records SET symbol = CONCAT('sz', symbol) WHERE symbol REGEXP '^[03][0-9]{5}$';

-- 8xxxxx, 4xxxxx -> bj
UPDATE watchlist SET symbol = CONCAT('bj', symbol) WHERE symbol REGEXP '^[84][0-9]{5}$';
UPDATE stock_group_items SET symbol = CONCAT('bj', symbol) WHERE symbol REGEXP '^[84][0-9]{5}$';
UPDATE tdx_block_items SET symbol = CONCAT('bj', symbol) WHERE symbol REGEXP '^[84][0-9]{5}$';
UPDATE tdx_watchlist_items SET symbol = CONCAT('bj', symbol) WHERE symbol REGEXP '^[84][0-9]{5}$';
UPDATE stocks SET code = CONCAT('bj', code) WHERE code REGEXP '^[84][0-9]{5}$';
UPDATE cn_stock_basics SET symbol = CONCAT('bj', symbol) WHERE symbol REGEXP '^[84][0-9]{5}$';
UPDATE stock_history SET stock_code = CONCAT('bj', stock_code) WHERE stock_code REGEXP '^[84][0-9]{5}$';
UPDATE stock_history_sh SET stock_code = CONCAT('bj', stock_code) WHERE stock_code REGEXP '^[84][0-9]{5}$';
UPDATE stock_history_sz SET stock_code = CONCAT('bj', stock_code) WHERE stock_code REGEXP '^[84][0-9]{5}$';
UPDATE stock_history_bj SET stock_code = CONCAT('bj', stock_code) WHERE stock_code REGEXP '^[84][0-9]{5}$';
UPDATE cn_finance_snapshots SET symbol = CONCAT('bj', symbol) WHERE symbol REGEXP '^[84][0-9]{5}$';
UPDATE yanbao_items SET stock_code = CONCAT('bj', stock_code) WHERE stock_code REGEXP '^[84][0-9]{5}$';
UPDATE archived_news SET symbol = CONCAT('bj', symbol) WHERE symbol REGEXP '^[84][0-9]{5}$';
UPDATE news_symbol_meta SET symbol = CONCAT('bj', symbol) WHERE symbol REGEXP '^[84][0-9]{5}$';
UPDATE signal_flag_pool SET code = CONCAT('bj', code) WHERE code REGEXP '^[84][0-9]{5}$';
UPDATE fingpt_predictions SET ticker = CONCAT('bj', ticker) WHERE ticker REGEXP '^[84][0-9]{5}$';
UPDATE fingpt_sentiment SET ticker = CONCAT('bj', ticker) WHERE ticker REGEXP '^[84][0-9]{5}$';
UPDATE kronos_predictions SET symbol = CONCAT('bj', symbol) WHERE symbol REGEXP '^[84][0-9]{5}$';
UPDATE analysis_reports SET symbol = CONCAT('bj', symbol) WHERE symbol REGEXP '^[84][0-9]{5}$';
UPDATE manager_trades SET symbol = CONCAT('bj', symbol) WHERE symbol REGEXP '^[84][0-9]{5}$';
UPDATE manager_positions_state SET symbol = CONCAT('bj', symbol) WHERE symbol REGEXP '^[84][0-9]{5}$';
UPDATE manager_holdings_snap SET symbol = CONCAT('bj', symbol) WHERE symbol REGEXP '^[84][0-9]{5}$';
UPDATE longhu_daily SET code = CONCAT('bj', code) WHERE code REGEXP '^[84][0-9]{5}$';
UPDATE ai_trading_records SET symbol = CONCAT('bj', symbol) WHERE symbol REGEXP '^[84][0-9]{5}$';
UPDATE ai_committee_selection_trades SET symbol = CONCAT('bj', symbol) WHERE symbol REGEXP '^[84][0-9]{5}$';
UPDATE em_hot_sector_members SET symbol = CONCAT('bj', symbol) WHERE symbol REGEXP '^[84][0-9]{5}$';
UPDATE user_race_trades SET symbol = CONCAT('bj', symbol) WHERE symbol REGEXP '^[84][0-9]{5}$';
UPDATE execution_records SET symbol = CONCAT('bj', symbol) WHERE symbol REGEXP '^[84][0-9]{5}$';

-- 完成
SELECT 'Migration complete!' AS status;
