#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
短线选股引擎 (优化版)
每日推荐3-5只短线机会股
排除创业板(3开头)和科创板(688开头)

优化内容：
1. 采用5大短线策略 (RSI, MACD, KDJ, 布林, 放量)
2. 动态止损止盈（基于ATR）
3. 精确买卖点输出
4. 多指标共振确认

评分体系 (满分100分):
- RSI信号: 20分
- KDJ信号: 20分
- MACD信号: 15分
- 布林带信号: 15分
- 量价异动: 15分
- 资金流向: 15分
"""

import pandas as pd
import numpy as np
from datetime import datetime
import json
from typing import List, Dict
from smart_data_source import SmartDataSource
from stock_cache_db import StockCache
from short_term_strategies import ShortTermStrategies

from selector_logging import get_selector_logger

logger = get_selector_logger(__name__)


class ShortTermSelector:
    """短线选股引擎"""
    
    def __init__(self):
        self.ds = SmartDataSource()
        self.cache = StockCache()
        self.strategies = ShortTermStrategies()
        
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
            
            # 如果缓存中没有，尝试从 stocks 表获取
            if not all_stocks:
                logger.info("缓存中没有全市场数据，尝试从 stocks 表获取...")
                all_stocks = self.cache.get_all_stocks(max_age_minutes=1440)
            
            if not all_stocks:
                logger.warning("没有获取到任何股票数据")
                return []
            
            logger.info("获取到 %s 只原始股票数据", len(all_stocks))
            
            if market == 'hs':
                # 沪深市场：主板（60开头）、中小板（00开头）
                filtered = [
                    stock['code'] for stock in all_stocks 
                    if stock['code'].startswith('60') or stock['code'].startswith('00')
                ]
                market_name = '沪深市场'
            elif market == 'chuang':
                # 双创：科创板（688开头）、创业板（300开头）
                filtered = [
                    stock['code'] for stock in all_stocks 
                    if stock['code'].startswith('688') or stock['code'].startswith('300')
                ]
                market_name = '双创市场'
            elif market == 'bj':
                # 北交所：8开头、4开头或92开头
                filtered = [
                    stock['code'] for stock in all_stocks 
                    if stock['code'].startswith('8') or stock['code'].startswith('4') or stock['code'].startswith('92')
                ]
                market_name = '北交所'
            else:
                # 全部市场，默认排除创业板和科创板
                filtered = [
                    stock['code'] for stock in all_stocks 
                    if not stock['code'].startswith('3') and not stock['code'].startswith('688')
                ]
                market_name = '全部市场（排除创业板和科创板）'
            
            logger.info("从 %s 加载了 %s 只股票", market_name, len(filtered))
            return filtered
        except Exception as e:
            logger.exception("加载股票列表失败: %s", e)
            return []
    
    def analyze_single_stock(self, code: str) -> Dict:
        """
        短线分析单只股票
        """
        try:
            # 获取历史数据（短线只需30天）
            df = self.ds.get_history_data(code, days=30)
            if df is None or df.empty or len(df) < 10:
                return None

            # 获取基础信息
            stock_info = self.cache.get_stock(code)
            if not stock_info:
                return None

            # 1. 技术面评分 (85分)
            tech_result = self.strategies.evaluate_all(df)
            score = tech_result['total_score']
            signals = tech_result['signals']
            details = tech_result['details']

            current_price = float(stock_info.get('price', df['close'].iloc[-1]))
            buy_signals = signals[:] # 策略返回的都是买入信号
            sell_signals = [] 

            # 2. 资金流向 (15分)
            fund_flow = self.cache.get_fund_flow(code)
            fund_score = 0
            fund_signal = None
            main_in_wan = 0

            if fund_flow:
                main_in = fund_flow.get('main_in', 0)
                main_in_wan = main_in / 10000  # 转换为万

                if main_in > 5000000:  # 主力流入>500万
                    fund_score = 15
                    fund_signal = f'主力流入 (+{main_in_wan:.0f}万)'
                    buy_signals.append(fund_signal)
                elif main_in > 0:
                    fund_score = 8
                    fund_signal = f'小幅流入 (+{main_in_wan:.0f}万)'
                elif main_in < -5000000:
                    fund_score = 0
                    fund_signal = f'主力流出 ({main_in_wan:.0f}万)'
                    sell_signals.append(fund_signal)

                if fund_signal:
                    signals.append(fund_signal.split(' ')[0])

            score += fund_score
            details['fund_flow'] = {
                'score': fund_score,
                'main_in': main_in_wan,
                'signal': fund_signal
            }

            # 3. ATR动态止损止盈
            atr = self.strategies.indicators.calc_atr_short(df)
            atr_now = atr.iloc[-1]

            trade_points = self.strategies.indicators.calc_trade_points(
                current_price, atr_now,
                stop_multiplier=2.0,
                profit_multiplier=3.0
            )

            details['trade_points'] = trade_points

            # 4. 汇总结果
            result = {
                'code': code,
                'name': stock_info.get('name', 'Unknown'),
                'price': current_price,
                'change_pct': float(stock_info.get('change_pct', 0)),
                'score': round(float(score), 2),
                'rating': self._get_rating(score),
                'signals': signals,
                'buy_signals': buy_signals,
                'sell_signals': sell_signals,
                'buy_signal_count': len(buy_signals),
                'sell_signal_count': len(sell_signals),
                'details': self._convert_to_json_safe(details),
                # 买卖点
                'buy_price': trade_points['buy_price'],
                'stop_loss': trade_points['stop_loss'],
                'take_profit': trade_points['take_profit'],
                'stop_loss_pct': trade_points['stop_loss_pct'],
                'take_profit_pct': trade_points['take_profit_pct'],
                'atr': trade_points['atr'],
                'atr_pct': trade_points['atr_pct'],
                'risk_reward_ratio': trade_points['risk_reward_ratio'],
                'recommend': bool(score >= 60 and len(buy_signals) >= 2),
                'update_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }

            return result

        except Exception as e:
            logger.exception("分析 %s 失败: %s", code, e)
            return None
    
    def _get_rating(self, score: float) -> str:
        """评级"""
        if score >= 85: return 'A+'
        elif score >= 70: return 'A'
        elif score >= 60: return 'B+'
        elif score >= 50: return 'B'
        else: return 'C'
    
    def _convert_to_json_safe(self, obj):
        """转换为JSON安全的数据类型"""
        import numpy as np
        import math
        
        if isinstance(obj, dict):
            return {k: self._convert_to_json_safe(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._convert_to_json_safe(item) for item in obj]
        elif isinstance(obj, (np.integer, np.int64, np.int32)):
            return int(obj)
        elif isinstance(obj, (np.floating, np.float64, np.float32)):
            val = float(obj)
            if math.isnan(val) or math.isinf(val): return None
            return val
        elif isinstance(obj, float):
            if math.isnan(obj) or math.isinf(obj): return None
            return obj
        elif isinstance(obj, np.bool_):
            return bool(obj)
        elif isinstance(obj, bool):
            return bool(obj)
        elif obj is None:
            return None
        else:
            return obj
    
    def select_top_stocks(self, top_n: int = 5, market: str = 'all') -> List[Dict]:
        """短线选股TOP N"""
        logger.info("=" * 60)
        logger.info("短线选股 - TOP %s", top_n)
        logger.info("=" * 60)
        
        watchlist = self.load_watchlist(market=market)
        if not watchlist:
            logger.warning("股票列表为空")
            return []
        
        logger.info("分析 %s 只股票...", len(watchlist))
        
        results = []
        success_count = 0
        fail_count = 0
        
        for i, code in enumerate(watchlist, 1):
            if i % 100 == 0 and i > 0:
                logger.info(
                    "已分析 %s/%s 只股票，成功: %s, 失败: %s",
                    i, len(watchlist), success_count, fail_count,
                )
            result = self.analyze_single_stock(code)
            if result:
                logger.debug(
                    "[%s/%s] %s -> %.1f 分 (%s)",
                    i, len(watchlist), code, result['score'], result['rating'],
                )
                results.append(result)
                success_count += 1
            else:
                logger.debug("[%s/%s] %s 跳过", i, len(watchlist), code)
                fail_count += 1
        
        logger.info("分析完成: 成功 %s 只, 失败 %s 只", success_count, fail_count)
        
        results.sort(key=lambda x: x['score'], reverse=True)
        top_stocks = results[:top_n]
        logger.info("返回评分最高的 %s 只股票", len(top_stocks))
        for stock in top_stocks:
            logger.info(
                "  - %s(%s): %s 分, 评级: %s, 推荐: %s",
                stock["name"], stock["code"], stock["score"], stock["rating"], stock["recommend"],
            )
        
        return top_stocks
    
    def generate_report(self, stocks: List[Dict]) -> str:
        """生成短线推荐报告"""
        report = []
        report.append("=" * 60)
        report.append(f"⚡ 短线选股报告")
        report.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("=" * 60)
        report.append("")

        for stock in stocks:
            report.append(f"【{stock['code']} {stock['name']}】评分: {stock['score']:.0f}分 ({stock['rating']})")
            report.append(f"现价: ¥{stock['price']:.2f} ({stock['change_pct']:+.2f}%)")
            if stock.get('buy_signals'):
                report.append("📈 信号: " + ", ".join(stock['buy_signals']))
            report.append(f"建议: 买点¥{stock['buy_price']:.2f}, 止损¥{stock['stop_loss']:.2f}, 止盈¥{stock['take_profit']:.2f}")
            report.append("-" * 60)
            report.append("")

        return "\n".join(report)
    
    def close(self):
        """关闭资源 - 注意：不关闭共享缓存连接"""
        self.ds.close()
        # 注意：不要关闭 cache，因为 CacheFactory 使用单例模式
        # self.cache.close()


if __name__ == '__main__':
    selector = ShortTermSelector()
    top_stocks = selector.select_top_stocks(top_n=5)
    if top_stocks:
        logger.info("\n%s", selector.generate_report(top_stocks))
    selector.close()
