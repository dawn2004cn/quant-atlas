
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""运行通达信日K线增量同步"""

from pathlib import Path
import sys
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# 添加项目根目录到路径
base_dir = Path(__file__).parent
sys.path.insert(0, str(base_dir))

# 临时修复那个有BOM的文件
problem_file = base_dir / "app" / "infrastructure" / "repositories" / "investment_manager_repository.py"
if problem_file.exists():
    try:
        content = problem_file.read_text(encoding='utf-8-sig')
        problem_file.write_text(content, encoding='utf-8')
        print("Fixed BOM in investment_manager_repository.py")
    except Exception as e:
        print(f"Warning: Could not fix BOM: {e}")

from app.application.services.tdx_dayk_sync_service import TdxDaykSyncService

def main():
    print("=" * 60)
    print("TDX Dayk Incremental Sync")
    print("=" * 60)
    
    service = TdxDaykSyncService()
    
    # 先获取MySQL最新日期
    latest_date = service.get_mysql_latest_date()
    print(f"\nMySQL latest date: {latest_date}")
    
    # 运行全量同步 - 重新同步所有日期
    print(f"\nStarting full sync from 2026-04-22...")
    result = service.full_sync_from_tdx_dayk(
        start_date="2026-04-22",
        dump_qlib_bin=False,
    )
    
    print("\n" + "=" * 60)
    print("Sync Result:")
    print("=" * 60)
    print(f"OK: {result.get('ok')}")
    print(f"Mode: {result.get('mode')}")
    if 'start_date' in result:
        print(f"Start date: {result.get('start_date')}")
    if 'stats' in result:
        stats = result['stats']
        print(f"Stats: {stats}")
    if 'error' in result:
        print(f"Error: {result.get('error')}")
    
    print("\nDone!")

if __name__ == "__main__":
    main()

