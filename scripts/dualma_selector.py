#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
双均线策略选股器
"""

import pandas as pd
import numpy as np
from datetime import datetime
from typing import List, Dict
from smart_data_source import SmartDataSource
from cache_factory import CacheFactory
from advanced_long_term_indicators import AdvancedLongTermIndicators
from fundamental_data import FundamentalData

# 导入 ta 库
from ta.trend import SMAIndicator

from selector_logging import get_selector_logger

logger = get_selector_logger(__name__)


class DualMASelector:
    """双均线策略选股器"""
    
    def __init__(self):
        self.ds = SmartDataSource()
        self.cache = CacheFactory.get_cache()
        self.indicators = AdvancedLongTermIndicators()
        self.fundamental = FundamentalData()
        
    def load_watchlist(self, market: str = 'all') -> List[str]:
        """加载全市场股票列表，根据市场参数过滤
        
        Args:
            market: 'all' - 全部市场
                   'hs' - 沪深市场（主板、中小板）
                   'chuang' - 双创（科创板、创业板）
                   'bj' - 北交所
        """
        try:
            # 优先从 market_all_cache 获取全市场数据（允许24小时内的缓存）
            all_stocks = self.cache.get_market_all_cache(max_age_minutes=1440)
            
            if all_stocks:
                logger.info("从 market_all_cache 获取到 %s 只原始股票数据", len(all_stocks))
            else:
                # 如果缓存中没有，尝试从 stocks 表获取
                logger.info("缓存中没有全市场数据，尝试从 stocks 表获取...")
                all_stocks = self.cache.get_all_stocks(max_age_minutes=1440)
                if all_stocks:
                    logger.info("从 stocks 表获取到 %s 只原始股票数据", len(all_stocks))
                else:
                    logger.warning("没有获取到任何股票数据，使用默认股票列表")
                    # 使用默认股票列表作为 fallback
                    default_stocks = [
                        {'code': '600036', 'name': '招商银行'},
                        {'code': '601318', 'name': '中国平安'},
                        {'code': '600519', 'name': '贵州茅台'},
                        {'code': '000858', 'name': '五粮液'},
                        {'code': '000333', 'name': '美的集团'},
                        {'code': '601888', 'name': '中国中免'},
                        {'code': '600031', 'name': '三一重工'},
                        {'code': '002415', 'name': '海康威视'},
                        {'code': '601899', 'name': '紫金矿业'},
                        {'code': '601988', 'name': '中国银行'}
                    ]
                    all_stocks = default_stocks
                    logger.info("使用默认股票列表，共 %s 只股票", len(all_stocks))
            
            # 首先根据市场过滤
            if market == 'hs':
                # 沪深市场：主板（60开头）、中小板（00开头）
                filtered = [
                    stock for stock in all_stocks 
                    if stock['code'].startswith('60') or stock['code'].startswith('00')
                ]
                market_name = '沪深市场'
            elif market == 'chuang':
                # 双创：科创板（688开头）、创业板（300开头）
                filtered = [
                    stock for stock in all_stocks 
                    if stock['code'].startswith('688') or stock['code'].startswith('300')
                ]
                market_name = '双创市场'
            elif market == 'bj':
                # 北交所：8开头、4开头或92开头
                filtered = [
                    stock for stock in all_stocks 
                    if stock['code'].startswith('8') or stock['code'].startswith('4') or stock['code'].startswith('92')
                ]
                market_name = '北交所'
            else:
                # 全部市场
                filtered = all_stocks
                market_name = '全部市场'
            
            # 排除ST股
            non_st_stocks = []
            st_count = 0
            for stock in filtered:
                stock_name = stock.get('name', '')
                # 检查股票名称是否包含ST
                if isinstance(stock_name, str) and ('ST' in stock_name or '*ST' in stock_name):
                    st_count += 1
                else:
                    non_st_stocks.append(stock)
            
            # 转换为股票代码列表
            final_stocks = [stock['code'] for stock in non_st_stocks]
            
            logger.info("从 %s 加载了 %s 只股票，排除了 %s 只 ST 股", market_name, len(final_stocks), st_count)
            
            return final_stocks
        except Exception as e:
            logger.exception("加载股票列表失败: %s", e)
            # 发生异常时返回默认股票列表
            default_stocks = ['600036', '601318', '600519', '000858', '000333']
            logger.warning("发生异常，返回默认股票列表: %s", default_stocks)
            return default_stocks
    
    def analyze_single_stock(self, code: str) -> Dict:
        """
        分析单只股票
        返回综合评分和详细数据
        """
        try:
            # 优先从缓存中获取评分
            cached_score = self.cache.get_stock_selection_score(code)
            if cached_score:
                logger.debug("从缓存获取 %s 评分: %.1f 分", code, cached_score["score"])
                # 构造完整的结果对象
                stock_info = self.cache.get_stock(code)
                if stock_info:
                    result = {
                        'code': code,
                        'name': stock_info.get('name', 'Unknown'),
                        'price': float(stock_info.get('price', 0)),
                        'change_pct': float(stock_info.get('change_pct', 0)),
                        'score': cached_score['score'],
                        'rating': cached_score['rating'],
                        'details': cached_score['details'],
                        'buy_signals': [s['description'] for s in cached_score['details']['strategies']] if cached_score['details'].get('strategies') else ['双均线策略入选'],
                        'buy_signal_count': len(cached_score['details']['strategies']) if cached_score['details'].get('strategies') else 0,
                        'buy_price': float(stock_info.get('price', 0)),
                        'stop_loss': 0,  # 简单处理，实际应该从缓存中获取或重新计算
                        'take_profit': 0,  # 简单处理，实际应该从缓存中获取或重新计算
                        'stop_loss_pct': 0,  # 简单处理，实际应该从缓存中获取或重新计算
                        'take_profit_pct': 0,  # 简单处理，实际应该从缓存中获取或重新计算
                        'risk_reward_ratio': 0,  # 简单处理，实际应该从缓存中获取或重新计算
                        'recommend': cached_score['score'] >= 70,  # 双均线策略推荐门槛
                        'update_time': cached_score['update_time']
                    }
                    return result
            
            # 缓存中没有评分或已过期，重新计算
            logger.debug("重新计算 %s 评分 (双均线策略)", code)
            
            # 优先从缓存中获取历史数据
            history_data = self.cache.get_stock_history(code)
            if history_data and len(history_data) >= 60:
                logger.debug("从缓存获取 %s 历史数据: %s 条", code, len(history_data))
                # 转换为DataFrame
                df = pd.DataFrame(history_data)
                df['date'] = pd.to_datetime(df['date'])
                df.set_index('date', inplace=True)
                df = df.sort_index()
            else:
                # 缓存中没有数据，从线上获取
                logger.debug("从线上获取 %s 历史数据", code)
                df = self.ds.get_history_data(code, days=120)
                if df is None or df.empty or len(df) < 60:
                    logger.warning("股票 %s 历史数据不足", code)
                    return None
            
            stock_info = self.cache.get_stock(code)
            if not stock_info:
                logger.warning("股票 %s 基本信息缺失", code)
                return None

            # 计算双均线指标
            df['SMA_short'] = SMAIndicator(close=df['close'], window=20).sma_indicator()
            df['SMA_long'] = SMAIndicator(close=df['close'], window=60).sma_indicator()
            
            # 生成信号
            df['signal'] = 0
            # 金叉买入
            buy_cond = (df['SMA_short'] > df['SMA_long']) & (df['SMA_short'].shift(1) <= df['SMA_long'].shift(1))
            # 死叉卖出
            sell_cond = (df['SMA_short'] < df['SMA_long']) & (df['SMA_short'].shift(1) >= df['SMA_long'].shift(1))
            
            df.loc[buy_cond, 'signal'] = 1
            df.loc[sell_cond, 'signal'] = -1
            
            # 计算评分
            # 最近是否有金叉
            recent_buy_signal = df['signal'].tail(20).sum() > 0
            # 短期均线是否在长期均线上方
            short_above_long = df['SMA_short'].iloc[-1] > df['SMA_long'].iloc[-1]
            # 短期均线是否向上
            short_trend_up = df['SMA_short'].iloc[-1] > df['SMA_short'].iloc[-5]
            # 长期均线是否向上
            long_trend_up = df['SMA_long'].iloc[-1] > df['SMA_long'].iloc[-10]
            
            score = 0
            if recent_buy_signal:
                score += 30
            if short_above_long:
                score += 25
            if short_trend_up:
                score += 20
            if long_trend_up:
                score += 25
            
            # 确保评分在0-100之间
            score = min(100, max(0, score))
            
            # 获取评级
            rating = self._get_rating(score)
            
            # 生成策略描述
            strategies = []
            if recent_buy_signal:
                strategies.append({'description': '最近出现金叉', 'score': 30})
            if short_above_long:
                strategies.append({'description': '短期均线在长期均线上方', 'score': 25})
            if short_trend_up:
                strategies.append({'description': '短期均线向上', 'score': 20})
            if long_trend_up:
                strategies.append({'description': '长期均线向上', 'score': 25})
            
            details = {
                'strategies': strategies,
                'short_above_long': short_above_long,
                'short_trend_up': short_trend_up,
                'long_trend_up': long_trend_up,
                'recent_buy_signal': recent_buy_signal
            }
            
            # 保存评分到缓存
            self.cache.save_stock_selection_score(code, score, rating, details)
            
            # 计算当前价格，确保不为nan
            price_from_cache = stock_info.get('price')
            price_from_history = df['close'].iloc[-1] if len(df) > 0 else 0
            
            if price_from_cache:
                try:
                    current_price = float(price_from_cache)
                except (ValueError, TypeError):
                    current_price = price_from_history
            else:
                current_price = price_from_history
            
            # 确保价格有效
            if current_price <= 0:
                logger.warning("股票 %s 价格无效: %s", code, current_price)
                return None
            
            # 计算ATR值
            atr_series = self.indicators.calc_atr(df)
            if not atr_series.empty:
                atr_value = atr_series.iloc[-1]
                # 确保ATR值有效
                if atr_value <= 0:
                    atr_value = current_price * 0.05
            else:
                atr_value = current_price * 0.05

            # 计算止损止盈
            stop_loss = current_price - atr_value * 2.5
            take_profit = current_price + atr_value * 4.0
            
            # 确保止损价格合理
            if stop_loss <= 0:
                stop_loss = current_price * 0.9
            
            # 确保止盈价格合理
            if take_profit <= current_price:
                take_profit = current_price * 1.2
            
            # 双均线策略推荐门槛
            is_recommend = score >= 70
            
            # 计算涨跌幅
            change_pct_val = stock_info.get('change_pct', 0)
            try:
                change_pct = float(change_pct_val) if change_pct_val is not None else 0
            except (ValueError, TypeError):
                change_pct = 0
            
            result = {
                'code': code,
                'name': stock_info.get('name', 'Unknown'),
                'price': current_price,
                'change_pct': change_pct,
                'score': round(score, 2),
                'rating': rating,
                'details': details,
                'buy_signals': [s['description'] for s in strategies] if strategies else ['双均线策略综合评分入选'],
                'buy_signal_count': len(strategies) if strategies else 0,
                'buy_price': round(current_price, 2),
                'stop_loss': round(stop_loss, 2),
                'take_profit': round(take_profit, 2),
                'stop_loss_pct': round((stop_loss - current_price) / current_price * 100, 2),
                'take_profit_pct': round((take_profit - current_price) / current_price * 100, 2),
                'risk_reward_ratio': round((take_profit - current_price) / (current_price - stop_loss), 2) if (current_price - stop_loss) > 0 else 0,
                'recommend': is_recommend,
                'update_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }

            return result
            
        except Exception as e:
            logger.exception("分析股票 %s 时出错: %s", code, e)
            return None
    
    def _get_rating(self, score: float) -> str:
        if score >= 90: return 'A+'
        elif score >= 80: return 'A'
        elif score >= 70: return 'B+'
        elif score >= 60: return 'B'
        elif score >= 50: return 'C+'
        elif score >= 40: return 'C'
        else: return 'D'

    def select_top_stocks(self, top_n: int = 10, market: str = 'all') -> List[Dict]:
        # 检查缓存中是否有当天的选股报告
        today = datetime.now().strftime('%Y-%m-%d')
        cached_report = self.cache.get_stock_selection_report(today)
        
        # 只有当市场参数为'all'且缓存存在时才使用缓存
        # 如果指定了具体市场，不使用缓存，确保市场过滤生效
        if cached_report and market == 'all':
            logger.info("从缓存获取当天选股报告: %s", today)
            return cached_report['stocks']
        
        # 缓存中没有当天的报告，或指定了具体市场，重新生成
        logger.info("重新生成当天选股报告: %s (市场: %s, 策略: 双均线)", today, market)
        
        watchlist = self.load_watchlist(market=market)
        if not watchlist:
            logger.warning("没有加载到股票列表")
            return []
        
        logger.info("开始分析 %s 只股票...", len(watchlist))
        results = []
        success_count = 0
        fail_count = 0
        
        # 使用多线程提高选股速度
        import concurrent.futures
        from concurrent.futures import ThreadPoolExecutor
        
        def analyze_stock(code):
            # 在每个线程中创建完整的DualMASelector实例，确保线程安全
            thread_selector = DualMASelector()
            try:
                return thread_selector.analyze_single_stock(code)
            finally:
                # 关闭线程本地的连接
                thread_selector.close()
        
        # 设置线程池大小，减少线程数量以避免数据库锁定
        max_workers = min(8, len(watchlist))
        logger.info("使用 %s 个线程并行分析", max_workers)
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交所有任务
            future_to_code = {executor.submit(analyze_stock, code): code for code in watchlist}
            
            # 处理结果
            for i, future in enumerate(concurrent.futures.as_completed(future_to_code)):
                code = future_to_code[future]
                try:
                    result = future.result()
                    if result:
                        results.append(result)
                        success_count += 1
                    else:
                        fail_count += 1
                except Exception as e:
                    logger.warning("分析 %s 时出错: %s", code, e, exc_info=True)
                    fail_count += 1
                
                if (i + 1) % 100 == 0 or (i + 1) == len(watchlist):
                    logger.info("已分析 %s/%s 只股票，成功: %s, 失败: %s", i + 1, len(watchlist), success_count, fail_count)
        
        logger.info("分析完成: 成功 %s 只, 失败 %s 只", success_count, fail_count)
        
        # 按评分排序
        results.sort(key=lambda x: x['score'], reverse=True)
        
        # 返回前top_n个，不管是否推荐
        top_results = results[:top_n]
        logger.info("返回评分最高的 %s 只股票 (双均线策略)", len(top_results))
        for stock in top_results:
            logger.info("  - %s(%s): %s 分, 评级: %s, 推荐: %s", stock["name"], stock["code"], stock["score"], stock["rating"], stock["recommend"])
        
        # 生成并保存选股报告
        report = self.generate_report(top_results)
        self.cache.save_stock_selection_report(today, report, top_results)
        logger.info("已保存当天选股报告: %s", today)
        
        return top_results
    
    def generate_report(self, stocks: List[Dict]) -> str:
        report = ["="*60, f"📊 双均线策略中长线选股报告 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", "="*60, ""]
        for stock in stocks:
            report.extend([
                f"【{stock['name']} ({stock['code']})】",
                f"  评级: {stock['rating']} | 评分: {stock['score']:.1f}/100",
                f"  价格: ¥{stock['price']:.2f} ({stock['change_pct']:+.2f}%)",
                "  ✅ 触发策略:",
                *["      • " + s['description'] for s in stock['details']['strategies']],
                "  📈 技术指标:",
                f"      • 短期均线在长期均线上方: {stock['details'].get('short_above_long', False)}",
                f"      • 短期均线向上: {stock['details'].get('short_trend_up', False)}",
                f"      • 长期均线向上: {stock['details'].get('long_trend_up', False)}",
                f"      • 最近出现金叉: {stock['details'].get('recent_buy_signal', False)}",
                "💰 操作建议:",
                f"   买点: ¥{stock['buy_price']:.2f}",
                f"   止损: ¥{stock['stop_loss']:.2f} ({stock['stop_loss_pct']:.1f}%)",
                f"   止盈: ¥{stock['take_profit']:.2f} (+{stock['take_profit_pct']:.1f}%)",
                f"   盈亏比: {stock['risk_reward_ratio']:.1f}:1",
                "-"*60, ""
            ])
        return "\n".join(report)
    
    def close(self):
        """关闭资源 - 注意：不关闭共享缓存连接"""
        self.ds.close()
        # 注意：不要关闭 cache，因为 CacheFactory 使用单例模式
        # self.cache.close()
        self.fundamental.close()

if __name__ == '__main__':
    selector = DualMASelector()
    top_stocks = selector.select_top_stocks(top_n=5)
    if top_stocks:
        report = selector.generate_report(top_stocks)
        logger.info("%s", report)
        with open('dualma_recommendation.txt', 'w', encoding='utf-8') as f:
            f.write(report)
    selector.close()