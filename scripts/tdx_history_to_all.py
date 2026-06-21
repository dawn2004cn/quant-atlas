import os
import sys

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.application.services.tdx_dayk_sync_service import TdxDaykSyncService

if __name__ == '__main__':
    # 运行所有测试
    print("Starting TDX history sync...")
    clss = TdxDaykSyncService()
    
    print("\n=== Running full_sync_from_tdx_dayk ===")
    full_result = clss.full_sync_from_tdx_dayk()
    print(f"Full sync result: {full_result}")
    
    print("\n=== Running daily_sync_from_tdx_dayk ===")
    daily_result = clss.daily_sync_from_tdx_dayk()
    print(f"Daily sync result: {daily_result}")
    
    print("\nTDX history sync completed!")
