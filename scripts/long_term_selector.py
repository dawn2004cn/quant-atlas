#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
中长线选股引擎
每日推荐5-10只优质股票
综合多维度指标评分
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
from advanced_indicators import StockScreenerEngine, BreakoutDragonModel, OversoldReboundModel, TrendResonanceModel, TrendTrackingModel, MeanReversionModel, MomentumContinuationModel, VolumePriceSynergyModel, KDJSwingModel, Model_01_TrendResonance, Model_02_LotusOutWater, Model_03_MASqueezeBreakout, Model_04_ChannelPullback, Model_05_MACDZeroCross, Model_06_MACDBottomCross, Model_07_MACDBullishDivergence, Model_08_VolumeBreakout, Model_09_SmartMoneyAccumulation, Model_10_ThreeWhiteSoldiers, Model_11_KDJGoldenPit, Model_12_RSIOversoldReversal, Model_13_CCITurningStrong, Model_14_BIASExtremePanic, Model_15_DMIUnilateralTrend, Model_16_BBSqueezeBreakout, Model_17_BBLowerSupport, Model_18_ATRExpansion, Model_19_SingleBullishHold, Model_20_StrongTrendDip

from selector_logging import get_selector_logger

logger = get_selector_logger(__name__)

# 创建全局共享的StockScreenerEngine实例
global_screener = None

def get_global_screener():
    """获取全局共享的StockScreenerEngine实例"""
    global global_screener
    if global_screener is None:
        # 创建StockScreenerEngine实例
        global_screener = StockScreenerEngine()
        # 注册所有模型
        models = [
            BreakoutDragonModel(),
            OversoldReboundModel(),
            TrendResonanceModel(),
            TrendTrackingModel(),
            MeanReversionModel(),
            MomentumContinuationModel(),
            VolumePriceSynergyModel(),
            KDJSwingModel(),
            Model_01_TrendResonance(), 
            Model_02_LotusOutWater(), 
            Model_03_MASqueezeBreakout(), 
            Model_04_ChannelPullback(),
            Model_05_MACDZeroCross(), 
            Model_06_MACDBottomCross(), 
            Model_07_MACDBullishDivergence(),
            Model_08_VolumeBreakout(), 
            Model_09_SmartMoneyAccumulation(), 
            Model_10_ThreeWhiteSoldiers(),
            Model_11_KDJGoldenPit(), 
            Model_12_RSIOversoldReversal(), 
            Model_13_CCITurningStrong(),
            Model_14_BIASExtremePanic(),
            Model_15_DMIUnilateralTrend(), 
            Model_16_BBSqueezeBreakout(), 
            Model_17_BBLowerSupport(), 
            Model_18_ATRExpansion(),
            Model_19_SingleBullishHold(), 
            Model_20_StrongTrendDip()
        ]
        for model in models:
            global_screener.register_model(model)
        logger.info("成功创建全局共享的 StockScreenerEngine，注册了 %s 种模型", len(models))
    return global_screener

class LongTermSelector:
    """中长线选股引擎"""
    
    def __init__(self):
        self.ds = SmartDataSource()
        self.cache = CacheFactory.get_cache()
        self.indicators = AdvancedLongTermIndicators()
        self.fundamental = FundamentalData()
        # 使用全局共享的StockScreenerEngine实例
        self.screener = get_global_screener()
        
    def _register_all_models(self):
        """注册所有25种选股模型"""
        models = [
            BreakoutDragonModel(),
            OversoldReboundModel(),
            TrendResonanceModel(),
            TrendTrackingModel(),
            MeanReversionModel(),
            MomentumContinuationModel(),
            VolumePriceSynergyModel(),
            KDJSwingModel(),
            Model_01_TrendResonance(), 
            Model_02_LotusOutWater(), 
            Model_03_MASqueezeBreakout(), 
            Model_04_ChannelPullback(),
            Model_05_MACDZeroCross(), 
            Model_06_MACDBottomCross(), 
            Model_07_MACDBullishDivergence(),
            Model_08_VolumeBreakout(), 
            Model_09_SmartMoneyAccumulation(), 
            Model_10_ThreeWhiteSoldiers(),
            Model_11_KDJGoldenPit(), 
            Model_12_RSIOversoldReversal(), 
            Model_13_CCITurningStrong(),
            Model_14_BIASExtremePanic(),
            Model_15_DMIUnilateralTrend(), 
            Model_16_BBSqueezeBreakout(), 
            Model_17_BBLowerSupport(), 
            Model_18_ATRExpansion(),
            Model_19_SingleBullishHold(), 
            Model_20_StrongTrendDip()
        ]
        
        for model in models:
            self.screener.register_model(model)
        
        logger.info("成功注册 %s 种选股模型", len(models))

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
                    # 优先从缓存中获取历史数据来获取最新价格和涨跌幅
                    history_data = self.cache.get_stock_history(code)
                    current_price = 0
                    change_pct = 0
                    
                    if history_data and len(history_data) >= 2:
                        df = pd.DataFrame(history_data)
                        df['date'] = pd.to_datetime(df['date'])
                        df = df.sort_values('date')
                        # 获取最新价格
                        current_price = float(df['close'].iloc[-1]) if len(df) > 0 else 0
                        # 计算涨跌幅
                        if len(df) >= 2:
                            prev_close = float(df['close'].iloc[-2])
                            if prev_close > 0:
                                change_pct = (current_price - prev_close) / prev_close * 100
                    
                    # 如果历史数据不可用，尝试从stock_info获取
                    if current_price <= 0:
                        price_from_cache = stock_info.get('price')
                        if price_from_cache:
                            try:
                                current_price = float(price_from_cache)
                            except (ValueError, TypeError):
                                current_price = 0
                    
                    if change_pct == 0:
                        change_pct_val = stock_info.get('change_pct')
                        if change_pct_val:
                            try:
                                change_pct = float(change_pct_val)
                            except (ValueError, TypeError):
                                change_pct = 0
                    
                    # 确保价格有效
                    if current_price <= 0:
                        logger.warning("股票 %s 价格无效，尝试重新计算评分", code)
                    else:
                        result = {
                            'code': code,
                            'name': stock_info.get('name', 'Unknown'),
                            'price': current_price,
                            'change_pct': change_pct,
                            'score': cached_score['score'],
                            'rating': cached_score['rating'],
                            'details': cached_score['details'],
                            'buy_signals': [s['description'] for s in cached_score['details']['strategies']] if cached_score['details'].get('strategies') else ['综合评分入选'],
                            'buy_signal_count': len(cached_score['details']['strategies']) if cached_score['details'].get('strategies') else 0,
                            'buy_price': current_price,
                            'stop_loss': 0,  # 简单处理，实际应该从缓存中获取或重新计算
                            'take_profit': 0,  # 简单处理，实际应该从缓存中获取或重新计算
                            'stop_loss_pct': 0,  # 简单处理，实际应该从缓存中获取或重新计算
                            'take_profit_pct': 0,  # 简单处理，实际应该从缓存中获取或重新计算
                            'risk_reward_ratio': 0,  # 简单处理，实际应该从缓存中获取或重新计算
                            'recommend': cached_score['score'] >= 40,
                            'update_time': cached_score['update_time']
                        }
                        return result
            
            # 缓存中没有评分或已过期，重新计算
            logger.debug("重新计算 %s 评分", code)
            
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
                # 缓存中没有数据，返回None，不从线上获取
                logger.warning("股票 %s 历史数据不足，无法分析", code)
                return None
            
            stock_info = self.cache.get_stock(code)
            if not stock_info:
                logger.warning("股票 %s 基本信息缺失", code)
                return None

            # 使用StockScreenerEngine分析股票
            # 转换数据格式为小写列名
            df_clean = df.copy()
            df_clean.columns = [col.lower() for col in df_clean.columns]
            
            # 遍历所有模型进行评估
            triggered_models = []
            for model in self.screener.models:
                try:
                    res = model.evaluate(df_clean, self.screener.indicators)
                    if res is not None:
                        triggered_models.append({
                            'name': model.name,
                            'score': res.get('score', 0),
                            'reasons': res.get('reasons', ''),
                            'description': f"{model.name}: {res.get('reasons', '')}"
                        })
                except Exception as e:
                    # 忽略模型评估错误，继续下一个模型
                    pass
            
            # 计算综合评分
            if triggered_models:
                # 基础分 + 最高的模型评分
                base_score = 20
                max_model_score = max([m['score'] for m in triggered_models])
                total_score = base_score + max_model_score
                rating = self._get_rating(total_score)
            else:
                # 没有触发任何模型，给一个基础分
                total_score = 30
                rating = self._get_rating(total_score)
            
            # 从历史数据计算涨跌幅
            change_pct = 0
            if len(df) >= 2:
                prev_close = df['close'].iloc[-2]
                current_close = df['close'].iloc[-1]
                if prev_close > 0:
                    change_pct = (current_close - prev_close) / prev_close * 100
            
            # 计算当前价格
            current_price = df['close'].iloc[-1] if len(df) > 0 else 0
            
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
            
            # 只要触发了一个模型就推荐
            is_recommend = len(triggered_models) > 0
            
            details = {
                'strategies': triggered_models,
                'base_score': 20,
                'model_score': max_model_score if triggered_models else 0,
            }
            
            # 保存评分到缓存
            self.cache.save_stock_selection_score(code, total_score, rating, details)
            
            result = {
                'code': code,
                'name': stock_info.get('name', 'Unknown'),
                'price': current_price,
                'change_pct': change_pct,
                'score': round(total_score, 2),
                'rating': rating,
                'details': details,
                'buy_signals': [s['description'] for s in triggered_models] if triggered_models else ['未触发任何模型'],
                'buy_signal_count': len(triggered_models),
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
        if score >= 80: return 'A+'
        elif score >= 70: return 'A'
        elif score >= 60: return 'B+'
        elif score >= 50: return 'B'
        elif score >= 40: return 'C+'
        elif score >= 30: return 'C'
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
        logger.info("重新生成当天选股报告: %s (市场: %s)", today, market)
        
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
            # 在每个线程中创建LongTermSelector实例，使用全局共享的StockScreenerEngine
            thread_selector = LongTermSelector()
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
        logger.info("返回评分最高的 %s 只股票", len(top_results))
        for stock in top_results:
            logger.info("  - %s(%s): %s 分, 评级: %s, 推荐: %s", stock["name"], stock["code"], stock["score"], stock["rating"], stock["recommend"])
        
        # 生成并保存选股报告
        report = self.generate_report(top_results)
        self.cache.save_stock_selection_report(today, report, top_results)
        logger.info("已保存当天选股报告: %s", today)
        
        return top_results
    
    def generate_report(self, stocks: List[Dict]) -> str:
        report = ["="*60, f"📊 中长线选股报告 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", "="*60, ""]
        for stock in stocks:
            report.extend([
                f"【{stock['name']} ({stock['code']})】",
                f"  评级: {stock['rating']} | 评分: {stock['score']:.1f}/100",
                f"  价格: ¥{stock['price']:.2f} ({stock['change_pct']:+.2f}%)",
                "  ✅ 触发策略:",
                *["      • " + s['description'] for s in stock['details']['strategies']],
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
    selector = LongTermSelector()
    top_stocks = selector.select_top_stocks(top_n=5)
    if top_stocks:
        report = selector.generate_report(top_stocks)
        logger.info("%s", report)
        with open('long_term_recommendation.txt', 'w', encoding='utf-8') as f:
            f.write(report)
    selector.close()
