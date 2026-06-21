from app.modules.system.services.helpers.stock_metadata import get_stock_metadata_batch

result = get_stock_metadata_batch(['688012', '688008', '600519'])
print('Result:', result)
if result:
    for code, data in result.items():
        print(f'{code}: {data.get("industry", "NO INDUSTRY")}')