"""检查通达信数据最新日期"""
import struct
from pathlib import Path

tdx_root = Path(r'E:\tdx\通达信金融终端(开心果交易版)V2024.02')
day_dir = tdx_root / 'vipdoc'

def get_latest_date(file_path):
    """获取.day文件最新日期"""
    with open(file_path, 'rb') as f:
        f.seek(0, 2)  # 文件末尾
        file_size = f.tell()
        if file_size < 32:
            return None
        # 最后一条记录
        f.seek(-32, 2)
        data = f.read(32)
        if len(data) == 32:
            # 通达信.day格式: 日期是4字节整数(如20260612)
            date_int = struct.unpack('<I', data[0:4])[0]
            if date_int > 19900101 and date_int < 21000101:
                year = date_int // 10000
                month = (date_int % 10000) // 100
                day = date_int % 100
                return f"{year}-{month:02d}-{day:02d}"
    return None

# 检查上海市场
sh_day = day_dir / 'sh' / 'lday'
if sh_day.exists():
    files = list(sh_day.glob('sh*.day'))
    if files:
        latest = get_latest_date(files[0])
        print(f"上海市场最新日期: {latest}")

# 检查深圳市场
sz_day = day_dir / 'sz' / 'lday'
if sz_day.exists():
    files = list(sz_day.glob('sz*.day'))
    if files:
        latest = get_latest_date(files[0])
        print(f"深圳市场最新日期: {latest}")

# 检查北京市场
bj_day = day_dir / 'bj' / 'lday'
if bj_day.exists():
    files = list(bj_day.glob('bj*.day'))
    if files:
        latest = get_latest_date(files[0])
        print(f"北京市场最新日期: {latest}")