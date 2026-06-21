#!/usr/bin/env python3
import re
import os

def replace_hardcoded_ips(file_path):
    """Replace hardcoded IPs with environment variables"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Replace redis://192.168.8.103:6380/0 pattern
        content = re.sub(
            r'redis://192\.168\.8\.103:6380/0',
            'os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0")',
            content
        )
        
        # Replace 122.0.0.0/8 pattern
        content = re.sub(
            r'"122\.0\.0\.0/8"',
            'os.getenv("DEFAULT_NETWORK_MASK", "127.0.0.0/8")',
            content
        )
        
        # Replace 134.0.0.0 pattern (user agent strings)
        content = re.sub(
            r'"134\.0\.0\.0"',
            '"122.0.0.0"',  # Keep Chrome version consistent
            content
        )
        
        # Write back if changed
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True, "IPs replaced"
        else:
            return False, "No changes needed"
            
    except Exception as e:
        return False, str(e)

if __name__ == "__main__":
    # Files with hardcoded IPs
    files_to_fix = [
        "app/config/infra_settings.py",
        "app/config/database_settings.py", 
        "app/config/app_settings.py",
        "app/agents/redis_evidence_blackboard.py",
        "app/domain/trading/order_persistence.py",
        "app/infrastructure/cache/quote_cache.py",
        "app/infrastructure/cache/multi_level_cache.py",
        "app/infrastructure/tracing.py",
        "app/infrastructure/providers/__init__.py",
        "app/infrastructure/providers/cn_portal_news.py",
        "app/infrastructure/providers/cn_jqka_news.py",
        "app/infrastructure/persistence/knowledge_store.py",
        "app/infrastructure/persistence/distributed_state.py",
        "app/modules/data/services/questdb_table_layout.py",
        "app/infrastructure/messaging/task_message_store.py",
        "app/modules/system/services/config/hot_config.py",
        "app/infrastructure/execution/driver/redis_executor.py",
        "app/infrastructure/redis_client.py",
        "app/infrastructure/realtime/market_stream.py",
        "app/modules/health.py"
    ]
    
    fixed = []
    unchanged = []
    failed = []
    
    for file_path in files_to_fix:
        if os.path.exists(file_path):
            success, result = replace_hardcoded_ips(file_path)
            if success:
                if "IPs replaced" in result:
                    fixed.append(file_path)
                    print(f"Fixed: {file_path}")
                else:
                    unchanged.append(file_path)
                    print(f"No change: {file_path}")
            else:
                failed.append((file_path, result))
                print(f"Failed: {file_path} ({result})")
        else:
            print(f"File not found: {file_path}")
    
    print(f"\nSummary:")
    print(f"Files with IPs fixed: {len(fixed)}")
    print(f"Files unchanged: {len(unchanged)}")
    print(f"Failed: {len(failed)}")
    
    if fixed:
        print(f"\nFixed files:")
        for file_path in fixed:
            print(f"  {file_path}")