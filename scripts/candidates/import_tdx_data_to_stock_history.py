#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
一次性任务：将通达信的股票历史数据全部导入到 stock_history 表中
"""

import os
import sys
import time
from datetime import datetime
from typing import List, Dict

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(__file__))

from scripts.tdx.tdx_local_data_reader import TdxLocalDataReader
from ..stock_cache_db import StockCache
from ..config import TDX_ROOT_PATH

def import_tdx_data_to_stock_history():
    """将通达信本地数据导入到 stock_history 表"""
    print("开始导入通达信股票历史数据...")
    print(f"通达信路径: {TDX_ROOT_PATH}")
    
    # 初始化通达信数据读取器
    print("初始化通达信数据读取器...")
    tdx_reader = TdxLocalDataReader(TDX_ROOT_PATH)
    print("通达信数据读取器初始化完成")
    
    # 初始化缓存
    print("初始化 StockCache...")
    cache = StockCache()
    print("StockCache 初始化完成")
    
    # 市场列表
    markets = ['sh', 'sz', 'bj']
    
    # 统计信息
    total_files = 0
    success_count = 0
    failure_count = 0
    total_data_count = 0
    
    start_time = time.time()
    
    # 遍历每个市场
    for market in markets:
        print(f"\n处理市场: {market.upper()}")
        
        # 获取市场数据目录
        market_folder = tdx_reader._get_market_folder(market)
        print(f"市场目录: {market_folder}")
        
        if not os.path.exists(market_folder):
            print(f"市场目录不存在: {market_folder}")
            continue
        
        # 获取所有 .day 文件
        day_files = [f for f in os.listdir(market_folder) if f.endswith('.day')]
        print(f"找到 {len(day_files)} 个股票数据文件")
        
        total_files += len(day_files)
        
        # 逐个处理文件
        for i, day_file in enumerate(day_files, 1):
            try:
                # 提取股票代码
                stock_code = day_file.split('.')[0]
                print(f"[{i}/{len(day_files)}] 处理: {stock_code}")
                
                # 读取股票数据
                print(f"读取 {stock_code} 数据...")
                df = tdx_reader.get_stock_data(stock_code, adjust=True)  # 开启前复权
                print(f"读取完成，数据行数: {len(df)}")
                
                if df.empty:
                    print(f"{stock_code} 没有数据")
                    failure_count += 1
                    continue
                
                # 转换为保存格式
                print(f"转换 {stock_code} 数据格式...")
                history_data = []
                for index, row in df.iterrows():
                    date_str = index.strftime('%Y-%m-%d')
                    history_data.append({
                        'date': date_str,
                        'open': float(row['open']),
                        'high': float(row['high']),
                        'low': float(row['low']),
                        'close': float(row['close']),
                        'volume': float(row['volume']),
                        'amount': float(row.get('amount', 0))
                    })
                print(f"转换完成，数据条数: {len(history_data)}")
                
                # 保存历史数据
                print(f"保存 {stock_code} 历史数据...")
                cache.save_stock_history(stock_code, history_data)
                print(f"保存完成")
                
                # 统计信息
                success_count += 1
                total_data_count += len(history_data)
                
                # 显示进度
                latest_date = max(item['date'] for item in history_data)
                print(f"{stock_code} 导入成功: {len(history_data)} 条数据，最新日期: {latest_date}")
                
                # 每处理50个文件休息1秒，避免系统负载过高
                if i % 50 == 0:
                    print("休息1秒...")
                    time.sleep(1)
                    
            except Exception as e:
                print(f"处理 {day_file} 时出错: {e}")
                import traceback
                traceback.print_exc()
                failure_count += 1
                continue
    
    # 计算耗时
    end_time = time.time()
    elapsed_time = end_time - start_time
    
    # 打印统计结果
    print("\n" + "="*70)
    print("导入结果统计")
    print(f"总文件数: {total_files}")
    print(f"成功: {success_count}")
    print(f"失败: {failure_count}")
    print(f"导入数据条数: {total_data_count}")
    print(f"成功率: {(success_count / total_files * 100):.2f}%")
    print(f"耗时: {elapsed_time:.2f} 秒")
    print("="*70)
    
    # 关闭连接
    cache.close()
    print("\n通达信股票历史数据导入完成")

if __name__ == '__main__':
    import_tdx_data_to_stock_history()
