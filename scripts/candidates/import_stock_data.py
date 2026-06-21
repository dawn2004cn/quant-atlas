#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
将 stock_data 目录下的股票历史数据 CSV 文件导入到数据库缓存中
"""

import os
import sys
import csv
from datetime import datetime
from typing import List, Dict

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(__file__))

from stock_cache_db import StockCache

def import_stock_data():
    """导入股票历史数据"""
    print("🚀 开始导入股票历史数据...")
    
    # 初始化缓存
    cache = StockCache()
    
    # 股票数据目录
    stock_data_dir = os.path.join(os.path.dirname(__file__), 'stock_data')
    
    if not os.path.exists(stock_data_dir):
        print(f"❌ 股票数据目录不存在: {stock_data_dir}")
        return
    
    # 获取所有 CSV 文件
    csv_files = [f for f in os.listdir(stock_data_dir) if f.endswith('.csv')]
    print(f"📊 找到 {len(csv_files)} 个股票数据文件")
    
    # 统计信息
    success_count = 0
    failure_count = 0
    
    # 逐个处理 CSV 文件
    for i, csv_file in enumerate(csv_files, 1):
        try:
            # 提取股票代码
            stock_code = csv_file.split('.')[0]
            print(f"\n[{i}/{len(csv_files)}] 处理: {stock_code}")
            
            # 读取 CSV 文件
            csv_path = os.path.join(stock_data_dir, csv_file)
            history_data = []
            
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                rows = list(reader)
                
                # 跳过前 3 行（表头）
                for row in rows[3:]:
                    if len(row) < 6:
                        continue
                    
                    date_str = row[0]
                    close = float(row[1])
                    high = float(row[2])
                    low = float(row[3])
                    open_price = float(row[4])
                    volume = int(row[5])
                    
                    # 计算成交额
                    amount = close * volume
                    
                    history_data.append({
                        'date': date_str,
                        'open': open_price,
                        'high': high,
                        'low': low,
                        'close': close,
                        'volume': volume,
                        'amount': amount
                    })
            
            if not history_data:
                print(f"❌ {stock_code} 没有历史数据")
                failure_count += 1
                continue
            
            # 保存历史数据
            success = cache.save_stock_history(stock_code, history_data)
            
            if success:
                # 更新状态
                latest_date = max(item['date'] for item in history_data)
                cache.update_stock_history_status(stock_code, latest_date)
                print(f"✅ {stock_code} 导入成功: {len(history_data)} 条数据，最新日期: {latest_date}")
                success_count += 1
            else:
                print(f"❌ {stock_code} 导入失败")
                failure_count += 1
                
        except Exception as e:
            print(f"❌ 处理 {csv_file} 时出错: {e}")
            failure_count += 1
            continue
    
    # 打印统计结果
    print("\n" + "="*50)
    print("📋 导入结果统计")
    print(f"总文件数: {len(csv_files)}")
    print(f"成功: {success_count}")
    print(f"失败: {failure_count}")
    print(f"成功率: {(success_count / len(csv_files) * 100):.2f}%")
    print("="*50)
    
    # 关闭连接
    cache.close()
    print("\n✅ 股票历史数据导入完成")

if __name__ == '__main__':
    import_stock_data()
