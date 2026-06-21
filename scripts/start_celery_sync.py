
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""启动Celery增量同步任务"""

from pathlib import Path
import sys

base_dir = Path(__file__).parent
sys.path.insert(0, str(base_dir))

try:
    from app.tasks.tdx_dayk_tasks import tdx_dayk_incremental_sync

    print("=" * 60)
    print("启动通达信增量同步任务")
    print("=" * 60)
    
    # 启动异步任务
    result = tdx_dayk_incremental_sync.delay(start_date="2026-04-23")
    
    print(f"任务ID: {result.task_id}")
    print(f"任务状态: {result.status}")
    print("\n任务已提交到Celery队列，后台执行中...")
    print("可以使用 celery -A app.celery_app inspect active 查看任务状态")

except Exception as e:
    print(f"启动任务失败: {e}")
    print("\n尝试直接运行同步...")
    
    # 降级到直接执行
    from app.application.services.tdx_dayk_sync_service import TdxDaykSyncService
    
    service = TdxDaykSyncService()
    result = service.incremental_sync_from_tdx_dayk(
        start_date="2026-04-23",
        dump_qlib_bin=True,
        dump_max_workers=8,
    )
    
    print("\n同步完成!")
    print(f"成功: {result.get('ok')}")
    if 'stats' in result:
        stats = result['stats']
        print(f"同步统计: {stats}")
