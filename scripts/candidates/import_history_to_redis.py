#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
将A股历史数据导入Redis
"""

import os
import csv
import json
from datetime import datetime, timedelta
from redis_cache import RedisCache
from config import HISTORY_DATA_DIR

class HistoryDataImporter:
    def __init__(self):
        self.redis_cache = RedisCache()
        self.history_data_dir = HISTORY_DATA_DIR
        self.stock_data_dir = '../stock_data'
        # 计算三年前的日期
        self.three_years_ago = (datetime.now() - timedelta(days=3*365)).strftime('%Y-%m-%d')
    
    def prepare_history_data(self):
        """准备历史数据，确保stock_history_data目录中有所有股票的CSV文件"""
        if not os.path.exists(self.history_data_dir):
            os.makedirs(self.history_data_dir)
        
        # 复制stock_data目录中的CSV文件到stock_history_data目录
        if os.path.exists(self.stock_data_dir):
            for filename in os.listdir(self.stock_data_dir):
                if filename.endswith('.csv'):
                    source_path = os.path.join(self.stock_data_dir, filename)
                    target_path = os.path.join(self.history_data_dir, filename)
                    
                    # 读取源文件，只保留近三年的数据
                    with open(source_path, 'r', encoding='utf-8-sig') as src_file:
                        reader = csv.DictReader(src_file)
                        rows = []
                        # 自动检测日期列
                        fieldnames = reader.fieldnames
                        date_col = None
                        for col in fieldnames:
                            if 'date' in col.lower() or '日期' in col:
                                date_col = col
                                break
                        
                        if not date_col:
                            print(f"⚠️ {filename} 找不到日期列，跳过")
                            continue
                        
                        for row in reader:
                            if row.get(date_col) >= self.three_years_ago:
                                # 重命名日期列为'date'
                                row['date'] = row.pop(date_col)
                                rows.append(row)
                    
                    # 写入目标文件
                    if rows:
                        with open(target_path, 'w', newline='', encoding='utf-8') as dst_file:
                            fieldnames = ['date', 'open', 'high', 'low', 'close', 'volume', 'amount']
                            writer = csv.DictWriter(dst_file, fieldnames=fieldnames)
                            writer.writeheader()
                            writer.writerows(rows)
                        print(f"✅ 处理 {filename}: {len(rows)} 条记录")
                    else:
                        print(f"⚠️ {filename} 没有近三年的数据")
    
    def import_all_history_data(self):
        """导入所有历史数据到Redis"""
        if not os.path.exists(self.history_data_dir):
            print("❌ 历史数据目录不存在")
            return
        
        stock_files = [f for f in os.listdir(self.history_data_dir) if f.endswith('.csv')]
        total_stocks = len(stock_files)
        print(f"📊 开始导入 {total_stocks} 只股票的历史数据")
        
        imported_count = 0
        failed_count = 0
        
        for i, filename in enumerate(stock_files, 1):
            stock_code = filename.replace('.csv', '')
            file_path = os.path.join(self.history_data_dir, filename)
            
            print(f"\n{'-'*50}")
            print(f"{i}/{total_stocks} 导入 {stock_code}")
            
            try:
                history_data = self._read_csv_file(file_path)
                if history_data:
                    success = self.redis_cache.save_stock_history(stock_code, history_data)
                    if success:
                        imported_count += 1
                        # 更新历史数据状态
                        last_date = max(item['date'] for item in history_data)
                        self.redis_cache.update_stock_history_status(stock_code, last_date)
                        print(f"✅ 导入成功: {len(history_data)} 条记录")
                    else:
                        failed_count += 1
                        print(f"❌ 导入失败")
                else:
                    failed_count += 1
                    print(f"⚠️ 无数据")
            except Exception as e:
                failed_count += 1
                print(f"❌ 错误: {e}")
        
        print(f"\n{'='*50}")
        print(f"导入完成: 成功 {imported_count}, 失败 {failed_count}")
    
    def _read_csv_file(self, file_path):
        """读取CSV文件并返回历史数据列表"""
        history_data = []
        
        def safe_float(value, default=0):
            """安全转换为浮点数"""
            if not value or value == '':
                return default
            try:
                return float(value)
            except (ValueError, TypeError):
                return default
        
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # 确保所有必需字段存在
                if 'date' in row and 'close' in row:
                    close_value = safe_float(row['close'])
                    item = {
                        'date': row['date'],
                        'open': safe_float(row.get('open', close_value)),
                        'high': safe_float(row.get('high', close_value)),
                        'low': safe_float(row.get('low', close_value)),
                        'close': close_value,
                        'volume': safe_float(row.get('volume', 0)),
                        'amount': safe_float(row.get('amount', 0))
                    }
                    history_data.append(item)
        
        return history_data
    
    def export_history_data(self, stock_code, output_dir='exported_history'):
        """导出股票历史数据"""
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        history_data = self.redis_cache.get_stock_history(stock_code)
        if history_data:
            output_file = os.path.join(output_dir, f"{stock_code}.csv")
            with open(output_file, 'w', newline='', encoding='utf-8') as f:
                fieldnames = ['date', 'open', 'high', 'low', 'close', 'volume', 'amount']
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(history_data)
            print(f"✅ 导出 {stock_code} 历史数据到 {output_file}")
            return True
        else:
            print(f"❌ 未找到 {stock_code} 的历史数据")
            return False
    
    def export_all_history_data(self, output_dir='exported_history'):
        """导出所有股票历史数据"""
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        # 获取所有股票代码
        stock_codes = self.redis_cache.get_all_stocks_for_history()
        
        exported_count = 0
        failed_count = 0
        
        for stock_code in stock_codes:
            if self.export_history_data(stock_code, output_dir):
                exported_count += 1
            else:
                failed_count += 1
        
        print(f"\n{'='*50}")
        print(f"导出完成: 成功 {exported_count}, 失败 {failed_count}")

if __name__ == '__main__':
    importer = HistoryDataImporter()
    
    # 准备历史数据
    print("1. 准备历史数据...")
    importer.prepare_history_data()
    
    # 导入数据到Redis
    print("\n2. 导入数据到Redis...")
    importer.import_all_history_data()
    
    # 测试导出功能
    print("\n3. 测试导出功能...")
    importer.export_history_data('600519')
    
    print("\n🎉 所有操作完成!")
