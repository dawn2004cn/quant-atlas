#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
定时更新历史数据
功能：
1. 每天下午4:00自动更新历史数据
2. 支持手动触发更新
3. 记录更新日志
"""

import schedule
import time
import os
import logging
from update_history_data import HistoryDataUpdater
from smart_data_source import SmartDataSource
from datetime import datetime

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('history_update.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def update_daily_data():
    """更新当天的股票数据并追加到CSV文件中"""
    logger.info("开始更新当天股票数据...")
    try:
        # 初始化数据源和更新器
        ds = SmartDataSource()
        updater = HistoryDataUpdater()
        
        # 获取所有CSV文件
        csv_files = [f for f in os.listdir('stock_history_data') if f.endswith('.csv')]
        total = len(csv_files)
        success_count = 0
        
        logger.info(f"开始处理 {total} 只股票的当天数据")
        
        for i, csv_file in enumerate(csv_files, 1):
            stock_code = csv_file.replace('.csv', '')
            logger.info(f"[{i}/{total}] 处理: {stock_code}")
            
            try:
                # 获取实时数据
                data = ds.get_realtime_price(stock_code)
                if data:
                    # 构建当天数据
                    daily_data = {
                        'date': datetime.now().strftime('%Y-%m-%d'),
                        'open': data.get('open', 0),
                        'high': data.get('high', 0),
                        'low': data.get('low', 0),
                        'close': data.get('price', 0),
                        'volume': data.get('volume', 0),
                        'amount': data.get('amount', 0)
                    }
                    
                    # 追加到CSV文件
                    success = updater.append_daily_data(stock_code, daily_data)
                    if success:
                        success_count += 1
                else:
                    logger.warning(f"无法获取 {stock_code} 的实时数据")
            except Exception as e:
                logger.error(f"处理 {stock_code} 失败: {e}")
        
        logger.info(f"当天数据更新完成！成功: {success_count}/{total}")
        
        # 关闭连接
        updater.close()
    except Exception as e:
        logger.error(f"更新当天数据失败: {e}")

def update_history_data():
    """更新历史数据"""
    logger.info("开始更新历史数据...")
    try:
        # 先更新当天数据
        update_daily_data()
        
        # 再更新历史数据
        updater = HistoryDataUpdater()
        updater.update_all_stocks()
        updater.close()
        logger.info("历史数据更新完成")
    except Exception as e:
        logger.error(f"更新历史数据失败: {e}")

def main():
    """主函数"""
    logger.info("启动历史数据定时更新服务")
    
    # 每天下午4:00执行更新
    schedule.every().day.at("16:00").do(update_history_data)
    
    # 立即执行一次更新
    update_history_data()
    
    logger.info("定时任务已设置，每天16:00自动更新历史数据")
    
    # 运行调度器
    while True:
        schedule.run_pending()
        time.sleep(60)  # 每分钟检查一次

if __name__ == '__main__':
    main()
