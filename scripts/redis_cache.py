#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A股数据缓存管理 - Redis数据库
"""

import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import redis

class RedisCache:
    """Redis缓存类 - 使用连接池优化性能"""
    
    _connection_pool = None
    
    def __init__(self, host='localhost', port=6379, db=0):
        self.host = host
        self.port = port
        self.db = db
        self.redis_client = None
        self._connect()
    
    def _connect(self):
        """连接到Redis - 使用连接池"""
        try:
            # 使用连接池而不是每次创建新连接
            if RedisCache._connection_pool is None:
                RedisCache._connection_pool = redis.ConnectionPool(
                    host=self.host,
                    port=self.port,
                    db=self.db,
                    decode_responses=True,
                    max_connections=50,  # 最大连接数
                    socket_keepalive=True,
                    socket_keepalive_options={},
                    health_check_interval=30
                )
            
            self.redis_client = redis.Redis(connection_pool=RedisCache._connection_pool)
            # 测试连接
            self.redis_client.ping()
        except Exception as e:
            print(f"[ERROR] 连接Redis失败: {e}")
            self.redis_client = None
    
    def save_stock(self, code, stock):
        """保存单只股票数据"""
        if not self.redis_client:
            return
        
        key = f"stock:{code}"
        stock_data = {
            'code': stock['code'],
            'name': stock['name'],
            'price': str(stock['price']),
            'change_pct': str(stock['change_pct']),
            'volume': str(stock.get('volume', 0)),
            'amount': str(stock.get('amount', 0)),
            'turnover': str(stock.get('turnover', 0)),
            'update_time': datetime.now().isoformat()
        }
        self.redis_client.hset(key, mapping=stock_data)
        # 设置过期时间：7天
        self.redis_client.expire(key, 7 * 24 * 3600)
    
    def save_stocks(self, stocks_data: List[Dict]):
        """批量保存股票数据"""
        if not self.redis_client:
            return
        
        for stock in stocks_data:
            self.save_stock(stock['code'], stock)
    
    def get_stock(self, code: str) -> Optional[Dict]:
        """获取单只股票数据"""
        if not self.redis_client:
            return None
        
        key = f"stock:{code}"
        stock_data = self.redis_client.hgetall(key)
        if stock_data:
            return {
                'code': stock_data['code'],
                'name': stock_data['name'],
                'price': float(stock_data['price']) if stock_data['price'] and stock_data['price'] != 'None' else 0.0,
                'change_pct': float(stock_data['change_pct']) if stock_data['change_pct'] and stock_data['change_pct'] != 'None' else 0.0,
                'volume': float(stock_data['volume']) if stock_data['volume'] and stock_data['volume'] != 'None' else 0.0,
                'amount': float(stock_data['amount']) if stock_data['amount'] and stock_data['amount'] != 'None' else 0.0,
                'turnover': float(stock_data['turnover']) if stock_data['turnover'] and stock_data['turnover'] != 'None' else 0.0,
                'update_time': stock_data['update_time']
            }
        return None
    
    def get_all_stocks(self, max_age_minutes=30) -> List[Dict]:
        """获取所有股票（过期数据会被过滤）"""
        if not self.redis_client:
            return []
        
        stocks = []
        cutoff = datetime.now() - timedelta(minutes=max_age_minutes)
        
        # 遍历所有stock键
        for key in self.redis_client.scan_iter(match="stock:*"):
            stock_data = self.redis_client.hgetall(key)
            if stock_data:
                update_time = datetime.fromisoformat(stock_data['update_time'])
                if update_time > cutoff:
                    stocks.append({
                        'code': stock_data['code'],
                        'name': stock_data['name'],
                        'price': float(stock_data['price']),
                        'change_pct': float(stock_data['change_pct']),
                        'volume': float(stock_data['volume']),
                        'amount': float(stock_data['amount']),
                        'turnover': float(stock_data.get('turnover', 0)),
                        'update_time': stock_data['update_time']
                    })
        
        # 按涨跌幅排序
        stocks.sort(key=lambda x: x['change_pct'], reverse=True)
        return stocks
    
    def save_fund_flow(self, code: str, data: Dict):
        """保存主力资金数据"""
        if not self.redis_client:
            return
        
        key = f"fund_flow:{code}"
        fund_data = {
            'main_in': str(data['main_in']),
            'retail_in': str(data['retail_in']),
            'main_ratio': str(data['main_ratio']),
            'update_time': datetime.now().isoformat()
        }
        self.redis_client.hset(key, mapping=fund_data)
        # 设置过期时间：24小时
        self.redis_client.expire(key, 24 * 3600)
    
    def get_fund_flow(self, code: str, max_age_hours=24) -> Optional[Dict]:
        """获取主力资金数据"""
        if not self.redis_client:
            return None
        
        key = f"fund_flow:{code}"
        fund_data = self.redis_client.hgetall(key)
        if fund_data:
            update_time = datetime.fromisoformat(fund_data['update_time'])
            cutoff = datetime.now() - timedelta(hours=max_age_hours)
            if update_time > cutoff:
                return {
                    'main_in': float(fund_data['main_in']),
                    'retail_in': float(fund_data['retail_in']),
                    'main_ratio': float(fund_data['main_ratio']),
                    'update_time': fund_data['update_time']
                }
        return None
    
    def save_tech_indicators(self, code: str, data: Dict):
        """保存技术指标数据"""
        if not self.redis_client:
            return
        
        key = f"tech_indicators:{code}"
        tech_data = {
            'ma5': str(data.get('ma5', '')),
            'ma10': str(data.get('ma10', '')),
            'ma20': str(data.get('ma20', '')),
            'rsi': str(data.get('rsi', '')),
            'macd': str(data.get('macd', '')),
            'dif': str(data.get('dif', data.get('macd_dif', ''))),
            'dea': str(data.get('dea', data.get('macd_dea', ''))),
            'update_time': datetime.now().isoformat()
        }
        self.redis_client.hset(key, mapping=tech_data)
        # 设置过期时间：24小时
        self.redis_client.expire(key, 24 * 3600)
    
    def get_tech_indicators(self, code: str, max_age_hours=24) -> Optional[Dict]:
        """获取技术指标数据"""
        if not self.redis_client:
            return None
        
        key = f"tech_indicators:{code}"
        tech_data = self.redis_client.hgetall(key)
        if tech_data:
            update_time = datetime.fromisoformat(tech_data['update_time'])
            cutoff = datetime.now() - timedelta(hours=max_age_hours)
            if update_time > cutoff:
                return {
                    'ma5': float(tech_data['ma5']) if tech_data['ma5'] else None,
                    'ma10': float(tech_data['ma10']) if tech_data['ma10'] else None,
                    'ma20': float(tech_data['ma20']) if tech_data['ma20'] else None,
                    'rsi': float(tech_data['rsi']) if tech_data['rsi'] else None,
                    'macd': float(tech_data['macd']) if tech_data['macd'] else None,
                    'dif': float(tech_data['dif']) if tech_data['dif'] else None,
                    'dea': float(tech_data['dea']) if tech_data['dea'] else None,
                    'update_time': tech_data['update_time']
                }
        return None
    
    def save_lhb(self, code: str, data: Dict):
        """保存龙虎榜数据"""
        if not self.redis_client:
            return
        
        key = f"lhb:{code}"
        lhb_data = {
            'buy_amount': str(data.get('buy_amount', 0)),
            'sell_amount': str(data.get('sell_amount', 0)),
            'net_amount': str(data.get('net_amount', 0)),
            'update_time': datetime.now().isoformat()
        }
        self.redis_client.hset(key, mapping=lhb_data)
        # 设置过期时间：24小时
        self.redis_client.expire(key, 24 * 3600)
    
    def get_lhb(self, code: str, max_age_hours=24) -> Optional[Dict]:
        """获取龙虎榜数据"""
        if not self.redis_client:
            return None
        
        key = f"lhb:{code}"
        lhb_data = self.redis_client.hgetall(key)
        if lhb_data:
            update_time = datetime.fromisoformat(lhb_data['update_time'])
            cutoff = datetime.now() - timedelta(hours=max_age_hours)
            if update_time > cutoff:
                return {
                    'buy_amount': float(lhb_data['buy_amount']),
                    'sell_amount': float(lhb_data['sell_amount']),
                    'net_amount': float(lhb_data['net_amount']),
                    'update_time': lhb_data['update_time']
                }
        return None
    
    def get_cache_stats(self) -> Dict:
        """获取缓存统计信息"""
        if not self.redis_client:
            return {'stock_count': 0, 'latest_update': None, 'fund_flow_count': 0}
        
        # 股票数量
        stock_count = 0
        latest_update = None
        for key in self.redis_client.scan_iter(match="stock:*"):
            stock_data = self.redis_client.hgetall(key)
            if stock_data:
                stock_count += 1
                update_time = stock_data.get('update_time')
                if update_time:
                    if not latest_update or update_time > latest_update:
                        latest_update = update_time
        
        # 资金流数据量
        fund_count = 0
        for key in self.redis_client.scan_iter(match="fund_flow:*"):
            fund_count += 1
        
        return {
            'stock_count': stock_count,
            'latest_update': latest_update,
            'fund_flow_count': fund_count
        }
    
    def clear_old_data(self, days=7):
        """清理N天前的旧数据"""
        if not self.redis_client:
            return
        
        cutoff = datetime.now() - timedelta(days=days)
        
        # 清理股票数据
        for key in self.redis_client.scan_iter(match="stock:*"):
            stock_data = self.redis_client.hgetall(key)
            if stock_data:
                update_time = datetime.fromisoformat(stock_data.get('update_time', '1970-01-01T00:00:00'))
                if update_time < cutoff:
                    self.redis_client.delete(key)
        
        # 清理资金流数据
        for key in self.redis_client.scan_iter(match="fund_flow:*"):
            fund_data = self.redis_client.hgetall(key)
            if fund_data:
                update_time = datetime.fromisoformat(fund_data.get('update_time', '1970-01-01T00:00:00'))
                if update_time < cutoff:
                    self.redis_client.delete(key)
        
        # 清理龙虎榜数据
        for key in self.redis_client.scan_iter(match="lhb:*"):
            lhb_data = self.redis_client.hgetall(key)
            if lhb_data:
                update_time = datetime.fromisoformat(lhb_data.get('update_time', '1970-01-01T00:00:00'))
                if update_time < cutoff:
                    self.redis_client.delete(key)
    
    def save_fundamental_data(self, code: str, data: dict):
        """保存基本面数据"""
        if not self.redis_client:
            return
        
        key = f"fundamental:{code}"
        fundamental_data = {
            'pe': str(data.get('pe', '')),
            'peg': str(data.get('peg', '')),
            'roe': str(data.get('roe', '')),
            'update_time': datetime.now().isoformat()
        }
        self.redis_client.hset(key, mapping=fundamental_data)
        # 设置过期时间：30天
        self.redis_client.expire(key, 30 * 24 * 3600)
    
    def get_fundamental_data(self, code: str) -> Optional[dict]:
        """获取基本面数据"""
        if not self.redis_client:
            return None
        
        key = f"fundamental:{code}"
        fundamental_data = self.redis_client.hgetall(key)
        if fundamental_data:
            return {
                'pe': float(fundamental_data['pe']) if fundamental_data['pe'] else None,
                'peg': float(fundamental_data['peg']) if fundamental_data['peg'] else None,
                'roe': float(fundamental_data['roe']) if fundamental_data['roe'] else None,
                'update_time': fundamental_data['update_time']
            }
        return None

    def save_market_all_cache(self, stocks_data: List[Dict]):
        """保存全市场数据缓存"""
        if not self.redis_client:
            return
        
        key = "market_all_cache"
        data_json = json.dumps(stocks_data, separators=(',', ':'))
        self.redis_client.set(key, data_json)
        # 设置过期时间：30分钟
        self.redis_client.expire(key, 30 * 60)
        print(f"全市场数据已缓存: {len(stocks_data)} 只股票")
    
    def get_market_all_cache(self, max_age_minutes=15) -> Optional[List[Dict]]:
        """获取全市场数据缓存"""
        if not self.redis_client:
            return None
        
        key = "market_all_cache"
        data_json = self.redis_client.get(key)
        if data_json:
            try:
                data = json.loads(data_json)
                print(f"使用缓存的全市场数据: {len(data)} 只股票")
                return data
            except json.JSONDecodeError:
                print("缓存数据解析失败")
                return None
        return None

    # ============== 股票分组相关方法 ==============
    
    def create_stock_group(self, name: str, description: str = '') -> bool:
        """创建股票分组"""
        if not self.redis_client:
            return False
        
        if name == '自选股':
            print("❌ 不能创建名为'自选股'的分组")
            return False
        
        # 检查分组是否已存在
        group_id = self.redis_client.hget("stock_groups", name)
        if group_id:
            print(f"❌ 分组已存在: {name}")
            return False
        
        # 生成新的分组ID
        group_id = str(self.redis_client.incr("stock_group_id"))
        
        # 保存分组信息
        self.redis_client.hset("stock_groups", name, group_id)
        self.redis_client.hset(f"stock_group:{group_id}", mapping={
            'name': name,
            'description': description,
            'created_at': datetime.now().isoformat()
        })
        
        print(f"✅ 创建分组成功: {name}")
        return True
    
    def delete_stock_group(self, group_id: int) -> bool:
        """删除股票分组"""
        if not self.redis_client:
            return False
        
        # 检查是否是默认分组
        group_name = self.redis_client.hget(f"stock_group:{group_id}", 'name')
        if group_name == '自选股':
            print("❌ 不能删除默认分组'自选股'")
            return False
        
        # 删除分组信息
        self.redis_client.delete(f"stock_group:{group_id}")
        
        # 从stock_groups中删除
        for name, gid in self.redis_client.hgetall("stock_groups").items():
            if gid == str(group_id):
                self.redis_client.hdel("stock_groups", name)
                break
        
        # 删除分组成员
        self.redis_client.delete(f"stock_group:{group_id}:members")
        
        print(f"✅ 删除分组成功: ID {group_id}")
        return True
    
    def get_stock_groups(self) -> List[Dict]:
        """获取所有股票分组"""
        if not self.redis_client:
            return []
        
        groups = []
        default_group = None
        
        for name, group_id in self.redis_client.hgetall("stock_groups").items():
            group_info = self.redis_client.hgetall(f"stock_group:{group_id}")
            if group_info:
                group = {
                    'id': int(group_id),
                    'name': group_info['name'],
                    'description': group_info.get('description', ''),
                    'created_at': group_info.get('created_at')
                }
                if group['name'] == '自选股':
                    default_group = group
                else:
                    groups.append(group)
        
        # 确保自选股分组排在第一位
        if default_group:
            groups.insert(0, default_group)
        
        # 其他分组按创建时间排序
        groups.sort(key=lambda x: x['created_at'] if x['name'] != '自选股' else '')
        return groups
    
    def add_stock_to_group(self, stock_code: str, group_id: int) -> bool:
        """添加股票到分组"""
        if not self.redis_client:
            return False
        
        key = f"stock_group:{group_id}:members"
        # 检查股票是否已在分组中
        if self.redis_client.sismember(key, stock_code):
            print(f"⚠️ 股票 {stock_code} 已在分组 ID {group_id} 中")
            return False
        
        # 添加股票到分组
        self.redis_client.sadd(key, stock_code)
        print(f"✅ 添加股票 {stock_code} 到分组 ID {group_id}")
        return True
    
    def remove_stock_from_group(self, stock_code: str, group_id: int) -> bool:
        """从分组中移除股票"""
        if not self.redis_client:
            return False
        
        key = f"stock_group:{group_id}:members"
        self.redis_client.srem(key, stock_code)
        print(f"✅ 从分组 ID {group_id} 移除股票 {stock_code}")
        return True
    
    def get_stocks_by_group(self, group_id: int) -> List[str]:
        """获取分组中的所有股票代码"""
        if not self.redis_client:
            return []
        
        key = f"stock_group:{group_id}:members"
        return list(self.redis_client.smembers(key))
    
    def get_stock_groups_by_code(self, stock_code: str) -> List[int]:
        """获取股票所属的所有分组ID"""
        if not self.redis_client:
            return []
        
        groups = []
        for name, group_id in self.redis_client.hgetall("stock_groups").items():
            key = f"stock_group:{group_id}:members"
            if self.redis_client.sismember(key, stock_code):
                groups.append(int(group_id))
        return groups
    
    def get_default_group_id(self) -> int:
        """获取默认分组（自选股）的ID"""
        if not self.redis_client:
            return 1
        
        group_id = self.redis_client.hget("stock_groups", '自选股')
        if group_id:
            return int(group_id)
        
        # 如果自选股分组不存在，创建它
        group_id = str(self.redis_client.incr("stock_group_id"))
        self.redis_client.hset("stock_groups", '自选股', group_id)
        self.redis_client.hset(f"stock_group:{group_id}", mapping={
            'name': '自选股',
            'description': '默认自选股分组',
            'created_at': datetime.now().isoformat()
        })
        return int(group_id)

    def save_stock_history(self, stock_code: str, history_data: List[Dict]):
        """保存股票历史数据"""
        if not self.redis_client:
            return False
        
        key = f"stock_history:{stock_code}"
        pipeline = self.redis_client.pipeline()
        
        # 计算三年前的日期
        three_years_ago = (datetime.now() - timedelta(days=3*365)).strftime('%Y-%m-%d')
        
        # 批量添加历史数据
        for item in history_data:
            date = item['date']
            # 只保存近三年的数据
            if date >= three_years_ago:
                # 使用日期作为分数，数据作为值
                data_json = json.dumps(item)
                pipeline.zadd(key, {data_json: self._date_to_score(date)})
        
        # 执行批量操作
        try:
            pipeline.execute()
            print(f"✅ 保存 {stock_code} 历史数据: {len(history_data)} 条")
            return True
        except Exception as e:
            print(f"❌ 保存历史数据失败 {stock_code}: {e}")
            return False
    
    def get_stock_history(self, stock_code: str, start_date: str = None, end_date: str = None) -> List[Dict]:
        """获取股票历史数据"""
        if not self.redis_client:
            return []
        
        key = f"stock_history:{stock_code}"
        
        # 计算分数范围
        min_score = 0
        max_score = float('inf')
        
        if start_date:
            min_score = self._date_to_score(start_date)
        if end_date:
            max_score = self._date_to_score(end_date)
        
        # 获取数据
        history_data = self.redis_client.zrangebyscore(key, min_score, max_score)
        
        # 解析数据
        history = []
        for data_json in history_data:
            try:
                item = json.loads(data_json)
                history.append(item)
            except json.JSONDecodeError:
                pass
        
        return history
    
    def get_stock_history_status(self, stock_code: str) -> Optional[Dict]:
        """获取股票历史数据更新状态"""
        if not self.redis_client:
            return None
        
        key = f"stock_history_status:{stock_code}"
        status_data = self.redis_client.hgetall(key)
        if status_data:
            return {
                'last_updated_date': status_data.get('last_updated_date'),
                'last_check_date': status_data.get('last_check_date')
            }
        return None
    
    def update_stock_history_status(self, stock_code: str, last_updated_date: str):
        """更新股票历史数据状态"""
        if not self.redis_client:
            return
        
        key = f"stock_history_status:{stock_code}"
        status_data = {
            'last_updated_date': last_updated_date,
            'last_check_date': datetime.now().isoformat()
        }
        self.redis_client.hset(key, mapping=status_data)
    
    def get_all_stocks_for_history(self) -> List[str]:
        """获取所有需要更新历史数据的股票代码"""
        if not self.redis_client:
            # 默认的股票列表
            return [
                '600519', '601318', '600036', '600276', '601888',
                '000858', '000333', '002594', '002415', '000001'
            ]
        
        # 从stock键中提取股票代码
        stock_codes = []
        for key in self.redis_client.scan_iter(match="stock:*"):
            code = key.split(":")[1]
            stock_codes.append(code)
        
        # 如果没有股票代码，返回默认列表
        if not stock_codes:
            return [
                '600519', '601318', '600036', '600276', '601888',
                '000858', '000333', '002594', '002415', '000001'
            ]
        
        return stock_codes
    
    def save_market_movements(self, movements: List[Dict]):
        """保存市场异动数据"""
        if not self.redis_client:
            return False
        
        key = "market_movements"
        # 清空旧数据
        self.redis_client.delete(key)
        
        # 批量插入新数据
        pipeline = self.redis_client.pipeline()
        for movement in movements:
            data_json = json.dumps(movement)
            pipeline.lpush(key, data_json)
        
        try:
            pipeline.execute()
            print(f"保存市场异动数据: {len(movements)} 条")
            return True
        except Exception as e:
            print(f"保存市场异动数据失败: {e}")
            return False
    
    def get_market_movements(self, limit=20) -> List[Dict]:
        """获取市场异动数据"""
        if not self.redis_client:
            return []
        
        key = "market_movements"
        movements_data = self.redis_client.lrange(key, 0, limit-1)
        
        movements = []
        for data_json in movements_data:
            try:
                movement = json.loads(data_json)
                # 确保返回格式与StockCache一致
                movements.append({
                    'code': movement.get('code', ''),
                    'name': movement.get('name', ''),
                    'type': movement.get('type', ''),
                    'change': movement.get('change', ''),
                    'time': movement.get('time', '')
                })
            except json.JSONDecodeError:
                pass
        
        return movements
    
    def save_stock_selection_score(self, stock_code: str, score: float, rating: str, details: Dict):
        """保存选股评分"""
        if not self.redis_client:
            return
        
        key = f"stock_selection_score:{stock_code}"
        score_data = {
            'score': str(score),
            'rating': rating,
            'details': json.dumps(details),
            'update_time': datetime.now().isoformat()
        }
        self.redis_client.hset(key, mapping=score_data)
        # 设置过期时间：24小时
        self.redis_client.expire(key, 24 * 3600)
    
    def get_stock_selection_score(self, stock_code: str, max_age_hours=24) -> Optional[Dict]:
        """获取选股评分"""
        if not self.redis_client:
            return None
        
        key = f"stock_selection_score:{stock_code}"
        score_data = self.redis_client.hgetall(key)
        if score_data:
            update_time = datetime.fromisoformat(score_data['update_time'])
            cutoff = datetime.now() - timedelta(hours=max_age_hours)
            if update_time > cutoff:
                return {
                    'score': float(score_data['score']),
                    'rating': score_data['rating'],
                    'details': json.loads(score_data['details']),
                    'update_time': score_data['update_time']
                }
        return None
    
    def save_stock_selection_report(self, report_date: str, report: str, stocks: List[Dict]):
        """保存选股报告"""
        if not self.redis_client:
            return
        
        key = f"stock_selection_report:{report_date}"
        report_data = {
            'report': report,
            'stocks': json.dumps(stocks),
            'update_time': datetime.now().isoformat()
        }
        self.redis_client.hset(key, mapping=report_data)
        # 设置过期时间：7天
        self.redis_client.expire(key, 7 * 24 * 3600)
    
    def get_stock_selection_report(self, report_date: str) -> Optional[Dict]:
        """获取选股报告"""
        if not self.redis_client:
            return None
        
        key = f"stock_selection_report:{report_date}"
        report_data = self.redis_client.hgetall(key)
        if report_data:
            return {
                'report': report_data['report'],
                'stocks': json.loads(report_data['stocks']),
                'update_time': report_data['update_time']
            }
        return None
    
    def _date_to_score(self, date_str):
        """将日期转换为分数"""
        # 格式：YYYY-MM-DD 转换为 YYYYMMDD 作为分数
        return int(date_str.replace('-', ''))
    
    def clear_stock_history(self, stock_code: str) -> bool:
        """清空股票的历史记录"""
        if not self.redis_client:
            return False
        
        try:
            # 清空历史数据
            history_key = f"stock_history:{stock_code}"
            self.redis_client.delete(history_key)
            
            # 清空状态数据
            status_key = f"stock_history_status:{stock_code}"
            self.redis_client.delete(status_key)
            
            print(f"✅ 清空 {stock_code} 历史记录成功")
            return True
        except Exception as e:
            print(f"❌ 清空历史记录失败 {stock_code}: {e}")
            return False
    
    def save_market_sentiment_cache(self, sentiment_data: Dict):
        """保存市场情绪数据到缓存"""
        if not self.redis_client:
            return False
        
        key = "market_sentiment_cache"
        data_json = json.dumps(sentiment_data, separators=(',', ':'))
        self.redis_client.set(key, data_json)
        # 设置过期时间：7天
        self.redis_client.expire(key, 7 * 24 * 3600)
        print("市场情绪数据已缓存")
        return True
    
    def get_market_sentiment_cache(self) -> Optional[Dict]:
        """从缓存获取市场情绪数据"""
        if not self.redis_client:
            return None
        
        key = "market_sentiment_cache"
        data_json = self.redis_client.get(key)
        if data_json:
            try:
                data = json.loads(data_json)
                print("使用缓存的市场情绪数据")
                return data
            except json.JSONDecodeError:
                print("缓存数据解析失败")
                return None
        return None
    
    def get_historical_market_movements(self, limit=20) -> List[Dict]:
        """获取历史市场异动数据"""
        if not self.redis_client:
            return []
        
        # 尝试从缓存获取数据
        key = "market_movements"
        movements_data = self.redis_client.lrange(key, 0, limit-1)
        
        movements = []
        for data_json in movements_data:
            try:
                movement = json.loads(data_json)
                movements.append({
                    'code': movement.get('code', ''),
                    'name': movement.get('name', ''),
                    'type': movement.get('type', ''),
                    'change': movement.get('change', ''),
                    'time': movement.get('time', '')
                })
            except json.JSONDecodeError:
                pass
        
        return movements
    
    def close(self):
        """关闭Redis连接"""
        if self.redis_client:
            self.redis_client.close()


# ============== 测试代码 ==============

def test_redis_cache():
    print("🔍 测试Redis缓存...")
    
    cache = RedisCache()
    
    # 测试1: 保存数据
    print("\n1️⃣ 测试保存数据...")
    test_stocks = [
        {'code': '601318', 'name': '中国平安', 'price': 45.67, 'change_pct': 2.3, 'volume': 1000000, 'amount': 45670000},
        {'code': '600519', 'name': '贵州茅台', 'price': 1680.0, 'change_pct': -1.2, 'volume': 50000, 'amount': 84000000},
    ]
    cache.save_stocks(test_stocks)
    print("✅ 保存成功")
    
    # 测试2: 读取数据
    print("\n2️⃣ 测试读取数据...")
    stock = cache.get_stock('601318')
    if stock:
        print(f"✅ {stock['name']}: ¥{stock['price']} ({stock['change_pct']:+.2f}%)")
    
    # 测试3: 统计信息
    print("\n3️⃣ 缓存统计:")
    stats = cache.get_cache_stats()
    print(f"   股票数量: {stats['stock_count']}")
    print(f"   最新更新: {stats['latest_update']}")
    
    cache.close()
    print("\n✅ 测试完成!")


if __name__ == '__main__':
    test_redis_cache()