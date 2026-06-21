#!/usr/bin/env python3
"""运行信号旗历史回填任务，从2020-01-01开始重新生成信号旗数据。"""

import os
import sys

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.tasks.signal_flag_tasks import run_signal_flag_scan_sync, _build_trading_calendar
from app.infrastructure.database.stock_cache_db import StockCache
from datetime import datetime


def run_backfill():
    """运行信号旗历史回填任务"""
    print("开始信号旗历史回填任务...")
    print("=====================================")
    
    # 配置参数
    start_date = "2020-01-01"
    end_date = datetime.now().strftime("%Y-%m-%d")
    max_stocks = 800
    lookback_days = 160
    
    # 构建交易日历
    cache = StockCache.default()
    calendar = _build_trading_calendar(cache, start_date, end_date)
    
    print(f"计算交易日历：{start_date} 到 {end_date}")
    print(f"总交易天数：{len(calendar)}")
    print("=====================================")
    
    # 逐个日期运行信号旗扫描
    written_days = 0
    total_days = len(calendar)
    
    for i, date in enumerate(calendar):
        print(f"处理日期 {i+1}/{total_days}: {date}")
        
        try:
            # 运行信号旗扫描
            result = run_signal_flag_scan_sync(
                pool_date=date,
                max_stocks=max_stocks,
                lookback_days=lookback_days
            )
            
            # 检查是否成功写入
            if result.get("persisted", 0) > 0:
                written_days += 1
                print("Success: scanned %d stocks, hits %d, written %d" % (
                    result.get('scanned', 0), 
                    result.get('hits', 0), 
                    result.get('persisted', 0)
                ))
            else:
                print("No data: %s" % result.get('message', 'No data'))
                
        except Exception as e:
            print("Failed: %s" % str(e))
        
        print("-------------------------------------")
    
    print("=====================================")
    print(f"信号旗历史回填完成！")
    print(f"总交易天数：{total_days}")
    print(f"成功写入天数：{written_days}")
    print(f"完成率：{written_days/total_days*100:.2f}%")
    print("=====================================")


if __name__ == "__main__":
    run_backfill()
