#!/usr/bin/env python3
"""手动触发信号旗历史回填任务"""

import os
import sys

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.tasks.signal_flag_tasks import signal_flag_pool_backfill


def trigger_backfill():
    """触发信号旗历史回填任务"""
    print("触发信号旗历史回填任务...")
    print("=====================================")
    
    # 配置参数
    start_date = "2020-01-01"
    end_date = "2026-04-18"
    max_stocks = 200
    lookback_days = 160
    limit_days = 7  # 限制只处理最近7天的数据
    
    print(f"开始日期: {start_date}")
    print(f"结束日期: {end_date}")
    print(f"股票数量: {max_stocks}")
    print(f"回溯天数: {lookback_days}")
    print(f"限制天数: {limit_days}")
    print("=====================================")
    
    try:
        # 触发任务
        result = signal_flag_pool_backfill.delay(
            start_date=start_date,
            end_date=end_date,
            max_stocks=max_stocks,
            lookback_days=lookback_days,
            limit_days=limit_days
        )
        
        print(f"任务已触发，任务ID: {result.id}")
        print("=====================================")
        print("任务正在执行中，您可以通过以下命令查看任务状态:")
        print(f"celery -A app.celery_app:celery inspect task {result.id}")
        print("=====================================")
        
    except Exception as e:
        print(f"触发任务失败: {str(e)}")


if __name__ == "__main__":
    trigger_backfill()
