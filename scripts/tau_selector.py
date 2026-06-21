#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TAU 选股引擎
基于 Trend, Activity, Undervaluation 三个维度的中长线选股策略
"""

import pandas as pd
import numpy as np
from datetime import datetime
import json
from typing import List, Dict
from smart_data_source import SmartDataSource
from cache_factory import CacheFactory
from advanced_long_term_indicators import AdvancedLongTermIndicators
from fundamental_data import FundamentalData

# 导入 ta 库
from ta.trend import SMAIndicator, MACD
from ta.momentum import RSIIndicator

from selector_logging import get_selector_logger

logger = get_selector_logger(__name__)


class TauSelector:
    """TAU 选股引擎"""
    
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
                        'buy_signals': [s['description'] for s in cached_score['details']['strategies']] if cached_score['details'].get('strategies') else ['TAU策略入选'],
                        'buy_signal_count': len(cached_score['details']['strategies']) if cached_score['details'].get('strategies') else 0,
                        'buy_price': float(stock_info.get('price', 0)),
                        'stop_loss': 0,  # 简单处理，实际应该从缓存中获取或重新计算
                        'take_profit': 0,  # 简单处理，实际应该从缓存中获取或重新计算
                        'stop_loss_pct': 0,  # 简单处理，实际应该从缓存中获取或重新计算
                        'take_profit_pct': 0,  # 简单处理，实际应该从缓存中获取或重新计算
                        'risk_reward_ratio': 0,  # 简单处理，实际应该从缓存中获取或重新计算
                        'recommend': cached_score['score'] >= 70,  # TAU策略推荐门槛更高
                        'update_time': cached_score['update_time']
                    }
                    return result
            
            # 缓存中没有评分或已过期，重新计算
            logger.debug("重新计算 %s 评分 (TAU策略)", code)
            
            # 优先从缓存中获取历史数据
            history_data = self.cache.get_stock_history(code)
            if history_data and len(history_data) >= 30:
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
                if df is None or df.empty or len(df) < 30:
                    logger.warning("股票 %s 历史数据不足", code)
                    return None
            
            stock_info = self.cache.get_stock(code)
            if not stock_info:
                logger.warning("股票 %s 基本信息缺失", code)
                return None

            fundamental_data = self.fundamental.get_stock_fundamental(code)
            
            # 计算 TAU 三个维度的评分
            trend_score = self._calculate_trend_score(df)
            activity_score = self._calculate_activity_score(df, stock_info)
            undervaluation_score = self._calculate_undervaluation_score(fundamental_data)
            
            # 综合评分
            total_score = trend_score + activity_score + undervaluation_score
            rating = self._get_rating(total_score)
            
            # 生成策略描述
            strategies = []
            if trend_score >= 30:
                strategies.append({'description': '趋势强度高', 'score': trend_score})
            if activity_score >= 25:
                strategies.append({'description': '市场活跃度高', 'score': activity_score})
            if undervaluation_score >= 25:
                strategies.append({'description': '价值低估', 'score': undervaluation_score})
            
            details = {
                'strategies': strategies,
                'trend_score': trend_score,
                'activity_score': activity_score,
                'undervaluation_score': undervaluation_score,
            }
            
            # 保存评分到缓存
            self.cache.save_stock_selection_score(code, total_score, rating, details)
            
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
            
            # TAU策略推荐门槛更高
            is_recommend = total_score >= 70
            
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
                'score': round(total_score, 2),
                'rating': rating,
                'details': details,
                'buy_signals': [s['description'] for s in strategies] if strategies else ['TAU策略综合评分入选'],
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
    
    def _calculate_trend_score(self, df: pd.DataFrame) -> float:
        """计算趋势强度评分"""
        score = 0
        
        # 1. MA 趋势
        if len(df) >= 20:
            # 使用 ta 库计算20日均线
            ma20 = SMAIndicator(close=df['close'], window=20).sma_indicator()
            if not ma20.empty:
                # 价格位于20日均线上方
                if df['close'].iloc[-1] > ma20.iloc[-1]:
                    score += 10
                # 20日均线向上
                if len(ma20) >= 5 and ma20.iloc[-1] > ma20.iloc[-5]:
                    score += 10
        
        # 2. MACD 金叉
        try:
            # 使用 ta 库计算MACD
            macd_indicator = MACD(close=df['close'])
            macd = macd_indicator.macd()
            signal = macd_indicator.macd_signal()
            hist = macd_indicator.macd_diff()
            if not macd.empty and not signal.empty:
                # MACD 金叉
                if len(macd) >= 2 and macd.iloc[-1] > signal.iloc[-1] and macd.iloc[-2] <= signal.iloc[-2]:
                    score += 5
                # 柱状图由负转正
                if len(hist) >= 2 and hist.iloc[-1] > 0 and hist.iloc[-2] <= 0:
                    score += 5
        except:
            pass
        
        # 3. RSI 趋势
        try:
            # 使用 ta 库计算RSI
            rsi = RSIIndicator(close=df['close'], window=14).rsi()
            if not rsi.empty:
                # RSI 在50以上
                if rsi.iloc[-1] > 50:
                    score += 5
                # RSI 呈现上升趋势
                if len(rsi) >= 5 and rsi.iloc[-1] > rsi.iloc[-5]:
                    score += 5
        except:
            pass
        
        # 4. 价格形态
        if len(df) >= 10:
            # 价格突破近期高点
            recent_high = df['high'].tail(10).max()
            if df['close'].iloc[-1] >= recent_high:
                score += 5
            # 形成上升通道
            if len(df) >= 20:
                recent_low = df['low'].tail(20).min()
                if df['low'].iloc[-1] > recent_low:
                    score += 5
        
        return min(score, 40)  # 趋势强度最高40分
    
    def _calculate_activity_score(self, df: pd.DataFrame, stock_info: Dict) -> float:
        """计算市场活跃度评分"""
        score = 0
        
        # 1. 成交量
        if len(df) >= 5:
            avg_volume = df['volume'].tail(5).mean()
            latest_volume = df['volume'].iloc[-1]
            if avg_volume > 0:
                volume_ratio = latest_volume / avg_volume
                if volume_ratio > 2:
                    score += 10  # 放量
                elif volume_ratio > 1.5:
                    score += 7
                elif volume_ratio > 1:
                    score += 5
                else:
                    score += 2
        
        # 2. 换手率
        turnover = stock_info.get('turnover', 0)
        try:
            turnover = float(turnover)
            if turnover > 5:
                score += 10
            elif turnover > 3:
                score += 7
            elif turnover > 2:
                score += 5
            else:
                score += 2
        except:
            score += 2
        
        # 3. 资金流向
        fund_flow = self.cache.get_fund_flow(stock_info.get('code', ''))
        if fund_flow:
            main_in = fund_flow.get('main_in', 0)
            if main_in > 50000000:
                score += 10
            elif main_in > 10000000:
                score += 7
            elif main_in > 0:
                score += 5
            else:
                score += 2
        else:
            score += 2
        
        # 4. 波动幅度
        if len(df) >= 5:
            daily_changes = df['close'].pct_change().abs()
            avg_volatility = daily_changes.tail(5).mean()
            if 0.01 <= avg_volatility <= 0.05:
                score += 5  # 波动适中
            elif avg_volatility < 0.01:
                score += 2  # 过于平静
            else:
                score += 3  # 过于剧烈
        
        return min(score, 35)  # 市场活跃度最高35分
    
    def _calculate_undervaluation_score(self, fundamental_data: Dict) -> float:
        """计算价值低估评分"""
        score = 0
        
        if not fundamental_data:
            return 25  # 无基本面数据时给基础分
        
        # 1. 市盈率 (PE)
        pe = fundamental_data.get('pe', 0)
        try:
            pe = float(pe)
            if pe > 0 and pe < 15:
                score += 10
            elif pe >= 15 and pe < 20:
                score += 7
            elif pe >= 20 and pe < 30:
                score += 5
            else:
                score += 2
        except:
            score += 2
        
        # 2. 市净率 (PB)
        pb = fundamental_data.get('pb', 0)
        try:
            pb = float(pb)
            if pb > 0 and pb < 1:
                score += 10
            elif pb >= 1 and pb < 2:
                score += 7
            elif pb >= 2 and pb < 3:
                score += 5
            else:
                score += 2
        except:
            score += 2
        
        # 3. PEG 比率
        peg = fundamental_data.get('peg', 0)
        try:
            peg = float(peg)
            if peg > 0 and peg < 0.5:
                score += 5
            elif peg >= 0.5 and peg < 1:
                score += 3
            else:
                score += 1
        except:
            score += 1
        
        # 4. 股息率
        dividend_rate = fundamental_data.get('dividend_rate', 0)
        try:
            dividend_rate = float(dividend_rate)
            if dividend_rate > 5:
                score += 5
            elif dividend_rate > 3:
                score += 3
            elif dividend_rate > 2:
                score += 2
            else:
                score += 1
        except:
            score += 1
        
        return min(score, 35)  # 价值低估最高35分
    
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
        logger.info("重新生成当天选股报告: %s (市场: %s, 策略: TAU)", today, market)
        
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
            # 在每个线程中创建完整的TauSelector实例，确保线程安全
            thread_selector = TauSelector()
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
        logger.info("返回评分最高的 %s 只股票 (TAU策略)", len(top_results))
        for stock in top_results:
            logger.info("  - %s(%s): %s 分, 评级: %s, 推荐: %s", stock["name"], stock["code"], stock["score"], stock["rating"], stock["recommend"])
        
        # 生成并保存选股报告
        report = self.generate_report(top_results)
        self.cache.save_stock_selection_report(today, report, top_results)
        logger.info("已保存当天选股报告: %s", today)
        
        return top_results
    
    def generate_report(self, stocks: List[Dict]) -> str:
        report = ["="*60, f"📊 TAU 中长线选股报告 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", "="*60, ""]
        for stock in stocks:
            report.extend([
                f"【{stock['name']} ({stock['code']})】",
                f"  评级: {stock['rating']} | 评分: {stock['score']:.1f}/100",
                f"  价格: ¥{stock['price']:.2f} ({stock['change_pct']:+.2f}%)",
                "  ✅ 触发策略:",
                *["      • " + s['description'] for s in stock['details']['strategies']],
                "  📈 评分构成:",
                f"      • 趋势强度: {stock['details'].get('trend_score', 0):.1f}",
                f"      • 市场活跃度: {stock['details'].get('activity_score', 0):.1f}",
                f"      • 价值低估: {stock['details'].get('undervaluation_score', 0):.1f}",
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
    selector = TauSelector()
    top_stocks = selector.select_top_stocks(top_n=5)
    if top_stocks:
        report = selector.generate_report(top_stocks)
        logger.info("%s", report)
        with open('tau_recommendation.txt', 'w', encoding='utf-8') as f:
            f.write(report)
    selector.close()