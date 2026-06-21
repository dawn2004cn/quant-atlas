#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
选股服务
"""

import math
from datetime import datetime
from typing import List, Dict
from interfaces.selector_interface import SelectorInterface


class SelectorService:
    """选股服务"""
    
    def __init__(self):
        pass
    
    def select_long_term_stocks(self, top_n: int, market: str, strategy: str = 'classic') -> List[Dict]:
        """
        选择中长线股票
        
        Args:
            top_n: 选择数量
            market: 市场类型
            strategy: 选股策略，'classic', 'tau', 'dualma', 'bollingerrsi', 'emamacd', 'volumebreakout', 'stochastic', 'tdx'
            
        Returns:
            List[Dict]: 选股结果
        """
        try:
            if strategy == 'tau':
                from tau_selector import TauSelector
                selector = TauSelector()
                stocks = selector.select_top_stocks(top_n=top_n, market=market)
                selector.close()
            elif strategy == 'dualma':
                from dualma_selector import DualMASelector
                selector = DualMASelector()
                stocks = selector.select_top_stocks(top_n=top_n, market=market)
                selector.close()
            elif strategy == 'bollingerrsi':
                from bollinger_rsi_selector import BollingerRSISelector
                selector = BollingerRSISelector()
                stocks = selector.select_top_stocks(top_n=top_n, market=market)
                selector.close()
            elif strategy == 'emamacd':
                from ema_macd_selector import EMAMACDSelector
                selector = EMAMACDSelector()
                stocks = selector.select_top_stocks(top_n=top_n, market=market)
                selector.close()
            elif strategy == 'volumebreakout':
                from volume_breakout_selector import VolumeBreakoutSelector
                selector = VolumeBreakoutSelector()
                stocks = selector.select_top_stocks(top_n=top_n, market=market)
                selector.close()
            elif strategy == 'stochastic':
                from stochastic_selector import StochasticSelector
                selector = StochasticSelector()
                stocks = selector.select_top_stocks(top_n=top_n, market=market)
                selector.close()
            else:
                from long_term_selector import LongTermSelector
                selector = LongTermSelector()
                stocks = selector.select_top_stocks(top_n=top_n, market=market)
                selector.close()
            
            # 清理数据中的NaN值
            cleaned_stocks = []
            for stock in stocks:
                cleaned_stock = {k: self._clean_value(v) for k, v in stock.items()}
                cleaned_stocks.append(cleaned_stock)
            
            return cleaned_stocks
        except Exception as e:
            print(f"中长线选股失败: {e}")
            return []
    
    def select_short_term_stocks(self, top_n: int, market: str) -> List[Dict]:
        """
        选择短线股票
        
        Args:
            top_n: 选择数量
            market: 市场类型
            
        Returns:
            List[Dict]: 选股结果
        """
        try:
            from short_term_selector import ShortTermSelector
            selector = ShortTermSelector()
            stocks = selector.select_top_stocks(top_n=top_n, market=market)
            selector.close()
            return stocks
        except Exception as e:
            print(f"短线选股失败: {e}")
            return []
    
    def generate_long_term_report(self, stocks: List[Dict]) -> Dict:
        """
        生成中长线选股报告
        
        Args:
            stocks: 选股结果
            
        Returns:
            Dict: 报告数据
        """
        if not stocks:
            return {
                'status': 'error',
                'message': '无数据'
            }
        
        try:
            # 计算统计数据
            total_score = sum(stock.get('score', 0) for stock in stocks)
            avg_score = total_score / len(stocks) if stocks else 0
            
            # 安全处理股票数据，确保所有字段都有值
            processed_stocks = []
            for stock in stocks:
                # 处理strategies
                strategies = stock.get('details', {}).get('strategies', [])
                if strategies and isinstance(strategies, list):
                    reason = '\n'.join([s.get('description', '') for s in strategies])
                else:
                    reason = ''
                
                processed_stocks.append({
                    'code': stock.get('code', ''),
                    'name': stock.get('name', ''),
                    'score': float(stock.get('score', 0)),
                    'rating': stock.get('rating', ''),
                    'reason': reason
                })
            
            # 构建报告数据
            report_data = {
                'generate_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'summary': f'本次共选出 {len(stocks)} 只中长线投资标的，平均评分 {avg_score:.2f} 分。所有股票均符合中长线投资逻辑，具有良好的基本面和技术面表现。',
                'stock_count': len(stocks),
                'avg_score': float(avg_score),
                'stocks': processed_stocks,
                'investment_advice': [
                    '建议采用分批建仓策略，不要一次性满仓',
                    '设置合理的止损位，控制单笔交易风险',
                    '关注大盘趋势，在市场回调时分批买入',
                    '持有周期建议3-6个月，耐心等待趋势形成',
                    '定期回顾持仓，根据基本面变化调整策略'
                ],
                'risk_notice': '本报告仅供参考，不构成投资建议。投资有风险，入市需谨慎。请结合自身风险承受能力和投资目标做出决策。市场变化莫测，任何投资策略都存在失败的可能性。'
            }
            
            # 生成文本报告（用于下载）
            try:
                from long_term_selector import LongTermSelector
                selector = LongTermSelector()
                text_report = selector.generate_report(stocks)
                selector.close()
                # 包含文本报告版本
                report_data['text_report'] = text_report
            except Exception as e:
                print(f"生成文本报告失败: {e}")
                report_data['text_report'] = "文本报告生成失败"

            return report_data
        except Exception as e:
            print(f"生成中长线选股报告失败: {e}")
            return {
                'status': 'error',
                'message': str(e)
            }
    
    def generate_selector_report(self, selector_type: str, stocks: List[Dict]) -> Dict:
        """
        生成选股报告
        
        Args:
            selector_type: 选股类型 (short/long)
            stocks: 选股结果
            
        Returns:
            Dict: 报告数据
        """
        if not stocks:
            return {
                'status': 'error',
                'message': '无数据'
            }
        
        try:
            if selector_type == 'short':
                from short_term_selector import ShortTermSelector
                selector = ShortTermSelector()
                report = selector.generate_report(stocks)
                selector.close()
            else:
                from long_term_selector import LongTermSelector
                selector = LongTermSelector()
                report = selector.generate_report(stocks)
                selector.close()
            
            return {
                'status': 'success',
                'report': report
            }
        except Exception as e:
            print(f"生成选股报告失败: {e}")
            return {
                'status': 'error',
                'message': str(e)
            }
    
    def _clean_value(self, v):
        """
        清理值中的NaN和inf
        
        Args:
            v: 原始值
            
        Returns:
            清理后的值
        """
        if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
            return None
        return v
