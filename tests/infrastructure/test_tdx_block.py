#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from pytdx.reader import BlockReader
import pandas as pd
from collections import defaultdict

from pytdx.reader.block_reader import BlockReader_TYPE_GROUP
import csv

# 不依赖 app 模块
def test_tdx_block():
    # 通达信安装目录（请修改为你的实际路径）
    tdx_root = r"E:\tdx\通达信金融终端(开心果交易版)V2024.02"  # 示例路径
    
    # 检查路径是否存在
    tdx_path = Path(tdx_root)
    if not tdx_path.exists():
        print(f"Error: TDX path not found: {tdx_root}")
        return
    
    # 检查 block_zs.dat 文件是否存在
    block_file = tdx_path / "T0002" / "hq_cache" / "block_zs.dat"
    if not block_file.exists():
        print(f"Error: block_zs.dat not found at: {block_file}")
        return

    try:
        # 读取指数板块（block_zs.dat）
        print(f"Reading block_zs.dat from: {block_file}")
        df = BlockReader().get_df(
            str(block_file),
            result_type=BlockReader_TYPE_GROUP
        )

        print("\nBlock data:")
        print(df.head())

        # 获取某个具体板块下的个股
        block_name = "沪深300"  # 替换为你想要的板块名称
        stocks = df[df['blockname'] == block_name]['code_list'].tolist()

        print(f"\n板块 {block_name} 包含 {len(stocks)} 只个股：")
        if stocks:
            print(stocks[:10])  # 前10只示例
        else:
            print("No stocks found in this block")
    except Exception as e:
        print(f"Error reading block data: {e}")
        import traceback
        traceback.print_exc()


def test_tdx_block_group():
    tdx_root = r"E:\tdx\通达信金融终端(开心果交易版)V2024.02"  # 示例路径
    tdx_path = Path(tdx_root)
    
    if not tdx_path.exists():
        print(f"Error: TDX path not found: {tdx_root}")
        return
    
    files = {
        '指数': tdx_path / "T0002" / "hq_cache" / "block_zs.dat",
        '概念': tdx_path / "T0002" / "hq_cache" / "block_gn.dat",
        '风格': tdx_path / "T0002" / "hq_cache" / "block_fg.dat",
    }

    stock_to_blocks = defaultdict(list)

    for block_type, file_path in files.items():
        if not file_path.exists():
            print(f"Warning: {file_path} not found, skipping")
            continue
            
        try:
            print(f"\nReading {block_type} from: {file_path}")
            df = BlockReader().get_df(str(file_path))

            print(f"Data shape: {df.shape}")
            print(df.head())
            
            for _, row in df.iterrows():
                stock_code = row['code']
                block_name = row['blockname']
                block_type = row['block_type']
                stock_to_blocks[stock_code].append((block_type, block_name))
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
            import traceback
            traceback.print_exc()

    # 示例：查询某只股票所属板块
    code = "000001"
    print(f"\n股票 {code} 所属板块：")
    if code in stock_to_blocks:
        for btype, bname in stock_to_blocks[code]:
            print(f"  {btype} - {bname}")
    else:
        print("  No blocks found for this stock")


def scan_mk_codes_from_tdx_dayk(tdx_root: str) -> list[str]:
    """从通达信 vipdoc 扫描全市场 6 位代码（去重、升序）。"""
    tdx_path = Path(tdx_root)
    if not tdx_path.exists():
        print(f"Error: TDX path not found: {tdx_root}")
        return []
    
    out: set[str] = set()
    for sub, prefix in (("sh", "sh"), ("sz", "sz"), ("bj", "bj")):
        d = tdx_path / "vipdoc" / sub / "lday"
        if not d.is_dir():
            print(f"Warning: {d} not found, skipping")
            continue
        
        print(f"Scanning {d}...")
        count = 0
        for p in d.glob(f"{prefix}[0-9][0-9][0-9][0-9][0-9][0-9].day"):
            stem = p.stem.lower()
            out.add(stem)
            count += 1
        print(f"Found {count} files in {d}")
    
    codes = sorted(out)
    print(f"Total unique codes found: {len(codes)}")
    return codes

def write_to_csv(records, csv_file):
    with open(csv_file, "w", newline='', encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=["code", "name"])
        writer.writeheader()
        writer.writerows(records)

def read_tnf(tdx_root):
    tdx_root = r"E:\tdx\通达信金融终端(开心果交易版)V2024.02"  # 示例路径
    tdx_path = Path(tdx_root)

    if not tdx_path.exists():
        print(f"Error: TDX path not found: {tdx_root}")
        return

    files = {
        'sz': tdx_path / "T0002" / "hq_cache" / "szm.tnf",
        'sh': tdx_path / "T0002" / "hq_cache" / "shm.tnf",
        'bj': tdx_path / "T0002" / "hq_cache" / "bjm.tnf",
    }

    stocks = []

    for market, file_path in files.items():
        if not file_path.exists():
            print(f"Warning: {file_path} not found, skipping")
            continue
        
        with open(file_path, 'rb') as f:
            try:
                f.read(50)  # 跳过头部信息
                while True:
                    body = f.read(314) # 通达信文件固定的字节长度
                    if len(body) < 314:
                        break
                    # 根据通达信二进制格式解析代码(6位)和名称(8位或更多)
                    try:
                        code = body[0:6].decode('utf-8').strip('\x00')
                        print("code:", market+code)
                        stock_code = market+code
                        # 尝试使用 gbk 解码，失败时使用 utf-8
                        try:
                            name = body[23:31].decode('gbk').strip('\x00')
                            print("gbk name:", name)
                        except UnicodeDecodeError:
                            name = body[23:31].decode('utf-8', errors='ignore').strip('\x00')
                            print("utf-8 name:", name)
                        if code and name:
                            #stocks.append((stock_code, name))
                            stocks.append({"code": stock_code, "name": name})
                    except Exception as e:
                        # 跳过解码失败的记录
                        continue
            except Exception as e:
                print(f"Error reading {file_path}: {e}")
                continue
    return stocks

# 使用示例
# list_sz = read_tnf("C:/new_tdx/T0002/hq_cache/szm.tnf")
import struct
import pandas as pd


def parse_tdx_block_dat(file_path):
    block_data = []

    with open(file_path, 'rb') as f:
        # 1. 跳过文件头 (前 384 字节通常是头部和元数据)
        # 注意：不同版本头部长度可能略有差异，通常从 384 字节开始是正式数据
        f.seek(384)

        while True:
            # 2. 读取板块元数据 (9字节名称 + 9字节代码 + 2字节数量 + 2字节类型)
            header_buffer = f.read(22)
            if len(header_buffer) < 22:
                break

            # 解包：9s(名称), 9s(代码), H(数量), H(类型)
            name, code, count, b_type = struct.unpack('<9s9sHH', header_buffer)

            name = name.decode('gbk').strip('\x00')
            code = code.decode('gbk').strip('\x00')

            # 3. 根据 count 读取后续的股票代码列表 (每个代码占 7 字节)
            stocks = []
            for _ in range(count):
                stock_data = f.read(7)
                if len(stock_data) < 7:
                    break
                # 股票代码通常是 '0600000' 这种格式，第一位代表市场
                stock_code = stock_data.decode('gbk').strip('\x00')
                stocks.append(stock_code)

            block_data.append({
                "block_name": name,
                "block_code": code,
                "type": b_type,
                "stock_count": count,
                "stock_list": ",".join(stocks)
            })

    return pd.DataFrame(block_data)


# 使用示例
# df = parse_tdx_block_dat('C:/new_tdx/T0002/hq_cache/tdx_block_industry.dat')
# print(df.head())
if __name__ == '__main__':
    print("=" * 60)
    print("Testing TDX Block Reader")
    print("=" * 60)
    
    #test_tdx_block()
    
    print("\n" + "=" * 60)
    print("Testing TDX Block Groups")
    print("=" * 60)
    
    #test_tdx_block_group()
    
    print("\n" + "=" * 60)
    print("Scanning TDX Dayk Files")
    print("=" * 60)
    
    r = r"E:\tdx\通达信金融终端(开心果交易版)V2024.02"
    '''codes = scan_mk_codes_from_tdx_dayk(r)
    if codes:
        print(f"First 20 codes: {codes[:20]}")
    else:
        print("No codes found")
    stocks_list = read_tnf(r)
    # 写入 CSV 文件
    # write_to_csv(stocks_list, "stocks.csv")
    if stocks_list:
        print(f"Total stocks found: {len(stocks_list)}")
        print("First 20 stocks:")
        for stock in stocks_list[:20]:
            try:
                # 使用字典键而不是元组索引
                print(f"  {stock['code']} - {stock['name']}")
            except (UnicodeEncodeError, KeyError):
                # 跳过无法编码或格式不正确的股票
                continue
    else:
        print("No stocks found")
    print("\n" + "=" * 60)
    print("Test completed")
    print("=" * 60)'''
    df = parse_tdx_block_dat(r+'/T0002/hq_cache/tdx_block_industry.dat')
    print(df.head())
