"""手动触发研报数据更新脚本

用法:
    python scripts/manual_yanbao.py          # 同步执行
    python scripts/manual_yanbao.py --async  # 异步执行(Celery)
"""

import sys
import os
import argparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def main():
    parser = argparse.ArgumentParser(description="手动触发研报数据更新")
    parser.add_argument("--async", dest="async_mode", action="store_true", help="使用Celery异步执行")
    parser.add_argument("--days", type=int, default=30, help="回溯天数(默认30天)")
    args = parser.parse_args()
    
    # 直接导入触发导入链
    print("初始化应用...")
    
    from datetime import datetime, timedelta
    from app.config import AppSettings, BASE_DIR
    from app.infrastructure.repositories.deps import create_basic_market_data_repository
    from app.application.services.basic_market_data_service import BasicMarketDataService
    
    settings = AppSettings.from_env()
    repo = create_basic_market_data_repository(settings)
    
    svc = BasicMarketDataService(
        base_dir=BASE_DIR,
        tdx_root_path=settings.tdx_root_path,
        repository=repo,
    )
    
    # 获取当前最新日期
    print("检查现有数据...")
    current = repo.list_yanbao(limit=1)
    if current:
        max_date = current[0].get("publish_date")
        print(f"当前最新研报日期: {max_date}")
    else:
        max_date = None
        print("没有现有研报数据")
    
    # 计算日期范围
    today = datetime.now()
    start_date = today - timedelta(days=args.days)
    
    if max_date:
        try:
            existing = datetime.strptime(str(max_date), "%Y-%m-%d")
            if existing >= start_date:
                start_date = existing + timedelta(days=1)
        except:
            pass
    
    begin_str = start_date.strftime("%Y-%m-%d")
    end_str = today.strftime("%Y-%m-%d")
    
    print(f"抓取日期范围: {begin_str} -> {end_str}")
    
    if begin_str >= end_str:
        print("日期范围无效,已经是最新")
        return
    
    # 执行抓取
    if args.async_mode:
        print("使用Celery异步执行...")
        from app.celery_app import celery
        task = celery.send_task(
            "app.tasks.market_tasks.scheduled_yanbao",
            kwargs={},
            queue="default"
        )
        print(f"任务已提交: {task.id}")
    else:
        print("同步执行中...")
        try:
            result = svc.ingest_yanbao_eastmoney_api(
                begin=begin_str,
                end=end_str,
                page_size=200,
                max_pages=20,
                sleep_sec=0.2,
            )
            print(f"执行结果: {result}")
        except Exception as e:
            print(f"执行失败: {e}")
            # 尝试 HTML 方式
            print("尝试HTML方式...")
            result = svc.ingest_yanbao_eastmoney_html()
            print(f"HTML执行结果: {result}")
    
    # 验证
    print("验证数据...")
    try:
        new_current = repo.list_yanbao(limit=1)
        if new_current:
            print(f"更新后最新日期: {new_current[0].get('publish_date')}")
    except Exception as e:
        print(f"验证跳过 (DB连接问题): {e}")

if __name__ == "__main__":
    main()