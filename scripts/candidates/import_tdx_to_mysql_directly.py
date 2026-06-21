#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
直接从通达信 .day 文件读取数据并写入到 MySQL 的 stock_history 表中
"""

import os
import sys
import time
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.infrastructure.database.mysql_client import mysql_connect, ensure_mysql_schema
from app.infrastructure.database.mysql_settings import MysqlSettings
from app.infrastructure.tdx_local.lday_reader import read_lday_file
from app.infrastructure.tdx_local.paths import TdxLocalPaths, resolve_tdx_root
from app.infrastructure.mappers.symbol_normalizer import SymbolNormalizer

def import_tdx_to_mysql_directly():
    """直接从通达信 .day 文件导入到 MySQL"""
    print("开始直接从通达信导入数据到 MySQL...")
    
    # 初始化 MySQL 连接
    print("初始化 MySQL 连接...")
    mysql_settings = MysqlSettings(
        host=os.environ.get("MYSQL_HOST", "192.168.8.103"),
        port=int(os.environ.get("MYSQL_PORT", "3307")),
        user=os.environ.get("MYSQL_USER", "admin"),
        password=os.environ.get("MYSQL_PASSWORD") or "",
        database=os.environ.get("MYSQL_DATABASE", "a_stock_monitor")
    )
    
    try:
        conn = mysql_connect(mysql_settings, autocommit=True)
        print(f"MySQL 连接成功: {mysql_settings.describe()}")
        
        # 确保 MySQL 表结构存在
        print("确保 MySQL 表结构存在...")
        ensure_mysql_schema(conn)
        print("MySQL 表结构检查完成")
        
        # 通达信路径
        tdx_root = r"E:\tdx\通达信金融终端(开心果交易版)V2024.02"
        print(f"通达信路径: {tdx_root}")
        
        # 解析通达信根目录
        root = resolve_tdx_root(tdx_root)
        if root is None:
            print("无法解析通达信路径")
            return
        
        paths = TdxLocalPaths(root)
        
        # 市场列表
        markets = [('sh', True), ('sz', False)]
        
        # 统计信息
        total_files = 0
        success_count = 0
        failure_count = 0
        total_data_count = 0
        
        start_time = time.time()
        
        for market_name, is_sh in markets:
            print(f"\n处理市场: {market_name.upper()}")
            
            # 获取市场数据目录
            market_folder = paths.lday_folder(market_sh=is_sh)
            print(f"市场目录: {market_folder}")
            
            if not os.path.exists(market_folder):
                print(f"市场目录不存在: {market_folder}")
                continue
            
            # 获取所有 .day 文件
            day_files = [f for f in os.listdir(market_folder) if f.endswith('.day')]
            print(f"找到 {len(day_files)} 个股票数据文件")
            
            total_files += len(day_files)
            
            # 批量插入数据
            batch_size = 1000
            
            for i, day_file in enumerate(day_files, 1):
                try:
                    # 提取股票代码
                    stock_code = day_file.split('.')[0]
                    print(f"[{i}/{len(day_files)}] 处理: {stock_code}")
                    
                    # 读取 .day 文件
                    file_path = os.path.join(market_folder, day_file)
                    rows = read_lday_file(file_path, tail=None)
                    
                    if not rows:
                        print(f"{stock_code} 没有数据")
                        failure_count += 1
                        continue
                    
                    # 准备批量插入数据
                    data = []
                    for row in rows:
                        data.append((
                            f"CN:{stock_code[2:]}",  # 转换为 CN:xxx 格式
                            row['date'],
                            float(row['open']),
                            float(row['high']),
                            float(row['low']),
                            float(row['close']),
                            float(row['volume']),
                            float(row.get('amount', 0))
                        ))
                    
                    # 执行批量插入
                    mysql_cursor = conn.cursor()
                    sql = """
                        INSERT IGNORE INTO stock_history 
                        (stock_code, date, open, high, low, close, volume, amount) 
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """
                    
                    # 分批插入
                    for j in range(0, len(data), batch_size):
                        batch = data[j:j+batch_size]
                        mysql_cursor.executemany(sql, batch)
                        conn.commit()
                    
                    success_count += 1
                    total_data_count += len(rows)
                    
                    print(f"{stock_code} 导入成功: {len(rows)} 条数据")
                    
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
        
        # 关闭连接
        conn.close()
        
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
        
        print("\n通达信数据直接导入 MySQL 完成")
        
    except Exception as e:
        print(f"MySQL 操作失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    import_tdx_to_mysql_directly()
