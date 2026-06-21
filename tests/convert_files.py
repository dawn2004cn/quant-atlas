#!/usr/bin/env python3
import os

def convert_file_to_utf8(file_path):
    """Convert a file from GBK to UTF-8, fallback to utf-8 with replace"""
    try:
        # Try GBK first (common Chinese encoding)
        with open(file_path, 'rb') as f:
            content = f.read()
        
        # Try decoding as GBK
        try:
            text = content.decode('gbk')
        except UnicodeDecodeError:
            # Fallback to utf-8 with replace
            text = content.decode('utf-8', errors='replace')
        
        # Write as UTF-8
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(text)
        return True, "GBK"
    except Exception as e:
        return False, str(e)

if __name__ == "__main__":
    # Files identified as non-UTF-8
    files_to_convert = [
        "app\\__init__.py",
        "app\\agents\\research\\__init__.py",
        "app\\core\\engine.py",
        "app\\core\\i18n.py",
        "app\\core\\main.py",
        "app\\core\\mesh\\memory_fabric_stub.py",
        "app\\domain\\integration_catalog.py",
        "app\\domain\\alpha\\dynamic_strategy_synthesis.py",
        "app\\domain\\alpha\\high_fidelity_executor.py",
        "app\\domain\\alpha\\high_fidelity_research.py",
        "app\\domain\\alpha\\paper_trading.py",
        "app\\domain\\ports\\data_source_ports.py",
        "app\\domain\\ports\\signal_alert_ports.py",
        "app\\domain\\strategies\\plugin\\__init__.py",
        "app\\domain\\trading\\order_persistence.py",
        "app\\infrastructure\\tracing.py",
        "app\\infrastructure\\capabilities\\registry.py",
        "app\\infrastructure\\execution\\driver\\redis_executor.py",
        "app\\infrastructure\\execution\\driver\\__init__.py",
        "app\\infrastructure\\providers\\cn_tdx_gpcw_fields.py",
        "app\\infrastructure\\realtime\\market_stream.py",
        "app\\infrastructure\\tdx_local\\watchlist_reader.py",
        "app\\models\\oscillation.py",
        "app\\modules\\ai_agent\\services\\advanced_features_service.py",
        "app\\modules\\ai_agent\\services\\ai_trading_coach_service.py",
        "app\\modules\\data\\services\\research_pipeline_snapshot.py",
        "app\\modules\\data\\services\\tdx_dayk_sync_service.py",
        "app\\modules\\market_data\\services\\cn_quote_snapshot.py",
        "app\\modules\\strategy\\services\\analytics\\visual_data_reducer_service.py",
        "app\\resources\\agent_skills\\fundamental-filter\\example_signal_engine.py",
        "app\\resources\\agent_skills\\technical-basic\\example_signal_engine.py",
        "app\\tasks\\data_backfill_tasks.py"
    ]
    
    converted = []
    failed = []
    
    for file_path in files_to_convert:
        if os.path.exists(file_path):
            success, result = convert_file_to_utf8(file_path)
            if success:
                converted.append(file_path)
                print(f"Converted: {file_path} (from {result})")
            else:
                failed.append((file_path, result))
                print(f"Failed: {file_path} ({result})")
        else:
            print(f"File not found: {file_path}")
    
    print(f"\nSummary:")
    print(f"Successfully converted: {len(converted)}")
    print(f"Failed: {len(failed)}")
    
    if failed:
        print("\nFailed files:")
        for file_path, error in failed:
            print(f"  {file_path}: {error}")