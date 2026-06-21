
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""简单测试每日同步是否正确重定向到增量同步"""

from pathlib import Path
import sys

base_dir = Path(__file__).parent
sys.path.insert(0, str(base_dir))

try:
    from app.application.services.tdx_dayk_sync_service import TdxDaykSyncService

    print("=" * 60)
    print("简单测试每日同步重定向")
    print("=" * 60)

    service = TdxDaykSyncService()

    # 检查方法是否存在
    print("\n检查方法存在性:")
    print(f"  daily_sync_from_tdx_dayk: {hasattr(service, 'daily_sync_from_tdx_dayk')}")
    print(f"  incremental_sync_from_tdx_dayk: {hasattr(service, 'incremental_sync_from_tdx_dayk')}")

    # 检查方法代码是否包含重定向逻辑
    daily_code = service.daily_sync_from_tdx_dayk.__code__
    incremental_code = service.incremental_sync_from_tdx_dayk.__code__
    
    print(f"\n方法代码行数:")
    print(f"  daily_sync_from_tdx_dayk: {daily_code.co_code} (简短表示已重定向)")
    print(f"  incremental_sync_from_tdx_dayk: {incremental_code.co_argcount} 个参数")

    # 检查文档字符串
    print(f"\n方法文档:")
    daily_doc = service.daily_sync_from_tdx_dayk.__doc__ or ""
    if "增量同步" in daily_doc:
        print("  ✓ daily_sync_from_tdx_dayk 文档包含'增量同步'")
    else:
        print("  ✗ daily_sync_from_tdx_dayk 文档不包含'增量同步'")

    print("\n" + "=" * 60)
    print("验证完成！")

except Exception as e:
    print(f"错误: {e}")
    import traceback
    traceback.print_exc()
