#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
市场情绪评分
基于全市场5000+只A股的综合情绪评分（0-100分）
"""
import akshare as ak
import pandas as pd
from datetime import datetime, timedelta
import time
import json
import requests
from cache_factory import SmartCacheFactory
from enhanced_data_fetcher import get_data_fetcher

# 缓存配置
CACHE_KEY = 'market_sentiment_data'
CACHE_EXPIRY_MINUTES = 30  # 缓存30分钟

class MarketDataFetcher:
    """市场数据获取器 - 实现多种数据获取方案"""
    
    def __init__(self):
        self.cache = SmartCacheFactory.get_cache(data_type='market')
        self.data_fetcher = get_data_fetcher()
    
    def get_market_data_from_cache(self):
        """从缓存读取数据"""
        try:
            # 尝试从缓存获取数据
            cached_data = self.cache.get_market_all_cache(max_age_minutes=CACHE_EXPIRY_MINUTES)
            if cached_data:
                print("✅ 从缓存加载市场数据")
                df = pd.DataFrame(cached_data)
                # 转换数值列
                numeric_cols = ['price', 'change_pct', 'volume', 'amount', 'turnover']
                for col in numeric_cols:
                    if col in df.columns:
                        df[col] = pd.to_numeric(df[col], errors='coerce')
                return df
        except Exception as e:
            print(f"读取缓存失败: {e}")
        return None
    
    def save_market_data_to_cache(self, df):
        """保存数据到缓存"""
        try:
            # 转换为缓存格式
            stocks_data = []
            for _, row in df.iterrows():
                stock = {
                    'code': str(row.get('代码', '')),
                    'name': str(row.get('名称', '')),
                    'price': float(row.get('最新价', 0)),
                    'change_pct': float(row.get('涨跌幅', 0)),
                    'volume': float(row.get('成交量', 0)),
                    'amount': float(row.get('成交额', 0)),
                    'turnover': float(row.get('换手率', 0))
                }
                stocks_data.append(stock)
            
            self.cache.save_market_all_cache(stocks_data)
            print("✅ 市场数据已保存到缓存")
        except Exception as e:
            print(f"保存缓存失败: {e}")
    
    def fetch_from_akshare(self):
        """从akshare获取数据"""
        print("尝试从akshare获取全市场A股实时数据...")
        try:
            df = ak.stock_zh_a_spot_em()
            # 数据清洗和转换
            numeric_cols = ['最新价', '涨跌幅', '涨跌额', '成交量', '成交额', '振幅', '换手率', '市盈率-动态', '市净率', '总市值', '流通市值']
            for col in numeric_cols:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            
            # 过滤掉没有交易的股票 (成交量=0)
            df = df[df['成交量'] > 0].dropna(subset=['涨跌幅', '最新价'])
            
            if not df.empty:
                self.save_market_data_to_cache(df)
            
            return df
        except Exception as e:
            print(f"从akshare获取数据失败: {e}")
            return pd.DataFrame()

    def fetch_from_sina(self):
        """从新浪财经API获取数据"""
        print("尝试从新浪财经API获取数据...")
        try:
            url = 'http://vip.stock.finance.sina.com.cn/mkt/#stock_hs_up'
            # 新浪财经API返回的是HTML，需要解析
            # 这里使用简化的方式，实际项目中可能需要更复杂的解析
            print("新浪财经API需要复杂解析，暂时返回空数据")
            return pd.DataFrame()
        except Exception as e:
            print(f"从新浪财经获取数据失败: {e}")
            return pd.DataFrame()
    
    def fetch_from_local(self):
        """从本地存储获取数据"""
        print("尝试从本地存储获取数据...")
        try:
            # 尝试从本地文件读取数据
            import os
            local_file = os.path.join(os.path.dirname(__file__), 'stock_data', 'market_data.csv')
            if os.path.exists(local_file):
                df = pd.read_csv(local_file)
                print("从本地文件加载市场数据")
                return df
            else:
                print("本地市场数据文件不存在")
                return pd.DataFrame()
        except Exception as e:
            print(f"从本地存储获取数据失败: {e}")
            return pd.DataFrame()
    
    def fetch_from_enhanced_fetcher(self):
        """使用enhanced_data_fetcher获取更多股票数据"""
        print("尝试使用enhanced_data_fetcher获取数据...")
        try:
            # 获取更多股票代码
            stock_codes = [
                '000001', '000002', '000333', '000858', '002594',
                '600000', '600036', '600276', '600519', '601318',
                '601012', '601888', '603288', '000725', '002415',
                '601668', '601628', '600887', '600031', '601899',
                '000651', '000338', '002027', '000063', '000977',
                '600030', '601166', '601398', '600028', '601288',
                '600104', '600111', '600188', '600271', '600309',
                '600340', '600585', '600703', '600809', '601088'
            ]
            
            # 使用enhanced_data_fetcher获取数据
            all_data = []
            batch_size = 10
            
            for i in range(0, len(stock_codes), batch_size):
                batch_codes = stock_codes[i:i+batch_size]
                batch_data = self.data_fetcher.fetch_realtime_data(batch_codes)
                
                if batch_data:
                    for code, data in batch_data.items():
                        all_data.append({
                            '代码': code,
                            '名称': data.get('name', ''),
                            '最新价': data.get('price', 0),
                            '涨跌幅': data.get('change_pct', 0),
                            '涨跌额': data.get('change', 0),
                            '成交量': data.get('volume', 0),
                            '成交额': data.get('amount', 0),
                            '换手率': data.get('turnover', 0),
                            '振幅': 0,
                            '市盈率-动态': 0,
                            '市净率': 0,
                            '总市值': 0,
                            '流通市值': 0
                        })
                
                # 避免请求过于频繁
                time.sleep(0.5)
            
            if all_data:
                df = pd.DataFrame(all_data)
                print(f"使用enhanced_data_fetcher获取 {len(df)} 只股票数据")
                return df
            else:
                print("enhanced_data_fetcher返回空数据")
                return pd.DataFrame()
        except Exception as e:
            print(f"使用enhanced_data_fetcher获取数据失败: {e}")
            return pd.DataFrame()
    
    def fetch_from_tencent_realtime(self):
        """从腾讯实时接口获取市场数据"""
        print("尝试从腾讯实时接口获取数据...")
        try:
            # 获取更多热门股票的实时数据作为市场样本
            sample_codes = [
                '000001', '000002', '000333', '000858', '002594',
                '600000', '600036', '600276', '600519', '601318',
                '601012', '601888', '603288', '000725', '002415',
                '601668', '601628', '600887', '600031', '601899',
                '000651', '000338', '002027', '000063', '000977',
                '600030', '601166', '601398', '600028', '601288'
            ]
            
            realtime_data = self.data_fetcher.fetch_realtime_data(sample_codes)
            
            if realtime_data:
                # 转换为DataFrame格式
                stocks_data = []
                for code, data in realtime_data.items():
                    stocks_data.append({
                        '代码': code,
                        '名称': data.get('name', ''),
                        '最新价': data.get('price', 0),
                        '涨跌幅': data.get('change_pct', 0),
                        '涨跌额': data.get('change', 0),
                        '成交量': data.get('volume', 0),
                        '成交额': data.get('amount', 0),
                        '换手率': data.get('turnover', 0),
                        '振幅': 0,  # 腾讯接口不返回振幅
                        '市盈率-动态': 0,
                        '市净率': 0,
                        '总市值': 0,
                        '流通市值': 0
                    })
                
                df = pd.DataFrame(stocks_data)
                print(f"从腾讯实时接口获取 {len(df)} 只股票数据")
                return df
            else:
                print("腾讯实时接口返回空数据")
                return pd.DataFrame()
        except Exception as e:
            print(f"从腾讯实时接口获取数据失败: {e}")
            return pd.DataFrame()
    
    def get_all_a_stock_data(self, use_cache=True):
        """获取全市场A股数据，带多方案备选"""
        # 1. 尝试从缓存获取
        if use_cache:
            cached_df = self.get_market_data_from_cache()
            if cached_df is not None and not cached_df.empty:
                return cached_df
        
        # 2. 尝试从akshare获取
        df = self.fetch_from_akshare()
        if not df.empty:
            return df
        
        # 3. 尝试使用enhanced_data_fetcher获取更多数据
        df = self.fetch_from_enhanced_fetcher()
        if not df.empty:
            return df
        
        # 4. 尝试从腾讯实时接口获取
        df = self.fetch_from_tencent_realtime()
        if not df.empty:
            return df
        
        # 5. 尝试从新浪财经获取
        df = self.fetch_from_sina()
        if not df.empty:
            return df
        
        # 6. 尝试从本地存储获取
        df = self.fetch_from_local()
        if not df.empty:
            return df
        
        # 7. 所有方案都失败，返回空数据
        print("所有数据获取方案都失败")
        return pd.DataFrame()
    


# 创建全局数据获取器实例
market_data_fetcher = MarketDataFetcher()

def get_all_a_stock_data(use_cache=True):
    """获取全市场A股数据，带多方案备选"""
    return market_data_fetcher.get_all_a_stock_data(use_cache)

def calculate_market_sentiment(use_demo_data=False):
    """
    计算市场情绪评分 (0-100)
    
    维度:
    1. 涨跌家数比 (20%)
    2. 平均涨幅 (20%)
    3. 涨停/跌停比 (15%)
    4. 强势股占比 (15%)
    5. 成交活跃度 (10%)
    6. 波动率 (10%)
    7. 趋势强度 (10%)
    """
    # 不使用demo数据，直接获取真实数据
    df = get_all_a_stock_data()
    is_historical = False
    data_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    if df.empty:
        return {
            'score': 0, 'level': '无数据', 'emoji': '❓',
            'description': '无法获取市场数据',
            'stats': {'total': 0},
            'update_time': datetime.now().strftime('%H:%M:%S')
        }

    # 统一列名，处理不同数据源的不同列名
    column_mapping = {
        '涨跌幅': 'change_pct',
        '换手率': 'turnover',
        '振幅': 'amplitude',
        '总市值': 'total_market_cap',
        '最新价': 'price'
    }
    
    # 重命名列名
    for old_col, new_col in column_mapping.items():
        if old_col in df.columns:
            df = df.rename(columns={old_col: new_col})
    
    # 确保必要的列存在
    required_columns = ['change_pct', 'turnover', 'amplitude', 'total_market_cap', 'price']
    for col in required_columns:
        if col not in df.columns:
            # 如果缺少必要的列，使用默认值
            if col == 'change_pct':
                df[col] = 0.0
            elif col == 'turnover':
                df[col] = 0.0
            elif col == 'amplitude':
                df[col] = 0.0
            elif col == 'total_market_cap':
                df[col] = 1e9  # 默认10亿市值
            elif col == 'price':
                df[col] = 10.0

    total = len(df)
    gainers = len(df[df['change_pct'] > 0])
    losers = len(df[df['change_pct'] < 0])
    neutral = total - gainers - losers
    
    # 1. 涨跌家数比 (20%)
    gainer_loser_ratio = gainers / losers if losers > 0 else 5  # 极端情况处理
    score1 = min(max(gainer_loser_ratio - 0.5, 0), 4) * 25  # 映射到0-100
    
    # 2. 平均涨幅 (20%)
    avg_change = df['change_pct'].mean()
    score2 = (avg_change + 2) * 25  # -2% -> 0分, +2% -> 100分
    score2 = min(max(score2, 0), 100)

    # 3. 涨停/跌停比 (15%)
    limit_up = len(df[df['change_pct'] >= 9.9])
    limit_down = len(df[df['change_pct'] <= -9.9])
    limit_ratio = limit_up / limit_down if limit_down > 0 else 10
    score3 = min(limit_ratio, 10) * 10

    # 4. 强势股占比 (15%)
    strong_stocks = len(df[df['change_pct'] > 5])
    weak_stocks = len(df[df['change_pct'] < -5])
    strong_ratio = strong_stocks / total * 100
    score4 = min(strong_ratio * 5, 100) # 20%以上强势股即为100分

    # 5. 成交活跃度 (10%) - 平均换手率
    avg_turnover = df['turnover'].median() # 用中位数更稳健
    score5 = min(avg_turnover / 3 * 100, 100) # 3%换手率算比较活跃

    # 6. 波动率 (10%) - 平均振幅
    avg_volatility = df['amplitude'].median() if 'amplitude' in df.columns else 0
    score6 = min(avg_volatility / 5 * 100, 100) # 5%振幅算高波动

    # 7. 趋势强度 (10%) - 大盘股表现
    large_cap = df[df['total_market_cap'] > 1000e8] # 千亿以上
    large_cap_change = large_cap['change_pct'].mean() if not large_cap.empty else 0
    score7 = (large_cap_change + 1) * 50 # -1% -> 0分, +1% -> 100分
    score7 = min(max(score7, 0), 100)

    # 加权总分
    total_score = (score1 * 0.20 + score2 * 0.20 + score3 * 0.15 + 
                   score4 * 0.15 + score5 * 0.10 + score6 * 0.10 + 
                   score7 * 0.10)
    
    total_score = round(total_score)

    # 评级
    if total_score >= 80:
        level, emoji, desc = '极度乐观', '🥳', '市场情绪高涨，风险偏好极高，注意风险。'
    elif total_score >= 65:
        level, emoji, desc = '乐观', '😊', '市场情绪偏暖，多数股票上涨，适合积极操作。'
    elif total_score >= 45:
        level, emoji, desc = '中性', '😐', '市场情绪不明确，涨跌互现，建议谨慎。'
    elif total_score >= 25:
        level, emoji, desc = '悲观', '😟', '市场情绪偏冷，多数股票下跌，注意控制仓位。'
    else:
        level, emoji, desc = '极度悲观', '🥶', '市场情绪恐慌，普遍下跌，风险极高，建议观望。'

    return {
        'score': total_score,
        'level': level,
        'emoji': emoji,
        'description': desc,
        'stats': {
            'total': total,
            'gainers': gainers,
            'losers': losers,
            'neutral': neutral,
            'limit_up': limit_up,
            'limit_down': limit_down,
            'strong_stocks': strong_stocks,
            'weak_stocks': weak_stocks,
            'avg_change': round(avg_change, 2),
            'avg_turnover': round(avg_turnover, 2),
            'avg_volatility': round(avg_volatility, 2)
        },
        'is_historical': is_historical,
        'data_time': data_time,
        'update_time': datetime.now().strftime('%H:%M:%S')
    }

if __name__ == '__main__':
    # 测试函数
    sentiment = calculate_market_sentiment()
    import json
    print(json.dumps(sentiment, indent=2, ensure_ascii=False))
