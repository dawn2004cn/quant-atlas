#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试读取 Astock20260405.xls 文件中的代码和上市日期列
"""
import pandas as pd
import os
from datetime import datetime

# 测试文件路径
TEST_FILE = "../scripts/Astock20260405.xls"

def test_read_astock_file():
    """
    测试读取 Astock20260405.xls 文件中的代码和上市日期列
    """
    print(f"测试读取 {TEST_FILE} 文件...")
    
    # 检查文件是否存在
    if not os.path.exists(TEST_FILE):
        print(f"错误: 文件 {TEST_FILE} 不存在")
        return False
    
    try:
        # 尝试使用不同的方法读取文件
        try:
            # 首先尝试作为制表符分隔的文件读取
            print("尝试作为制表符分隔的文件读取...")
            df = pd.read_csv(TEST_FILE, sep='\t', encoding='utf-8')
            print("成功作为制表符分隔的文件读取")
        except:
            try:
                # 尝试使用 gbk 编码读取制表符分隔的文件
                print("尝试使用 gbk 编码读取制表符分隔的文件...")
                df = pd.read_csv(TEST_FILE, sep='\t', encoding='gbk')
                print("成功使用 gbk 编码读取制表符分隔的文件")
            except:
                try:
                    # 尝试作为普通 CSV 文件读取
                    print("尝试作为 CSV 文件读取...")
                    df = pd.read_csv(TEST_FILE, encoding='utf-8')
                    print("成功作为 CSV 文件读取")
                except:
                    try:
                        # 尝试使用 gbk 编码读取 CSV 文件
                        print("尝试使用 gbk 编码读取 CSV 文件...")
                        df = pd.read_csv(TEST_FILE, encoding='gbk')
                        print("成功使用 gbk 编码读取 CSV 文件")
                    except:
                        try:
                            # 尝试作为 Excel 文件读取
                            print("尝试作为 Excel 文件读取...")
                            df = pd.read_excel(TEST_FILE)
                            print("成功作为 Excel 文件读取")
                        except Exception as e:
                            print(f"读取文件失败: {e}")
                            return False
        
        # 打印文件列名
        print(f"\n文件列名: {df.columns.tolist()}")
        
        # 查找代码列
        possible_code_cols = ['code', 'Code', 'symbol', '股票代码', '代码']
        code_col = next((col for col in possible_code_cols if col in df.columns), None)
        if not code_col:
            print("未找到代码列")
            return False
        else:
            print(f"找到代码列: {code_col}")
        
        # 查找上市日期列
        possible_date_cols = ['上市日期', '上市时间', 'ipo_date', 'listing_date']
        date_col = next((col for col in possible_date_cols if col in df.columns), None)
        if not date_col:
            print("未找到上市日期列")
            return False
        else:
            print(f"找到上市日期列: {date_col}")
        
        # 测试读取前10行数据
        print("\n前10行数据:")
        sample_data = df[[code_col, date_col]].head(10)
        for index, row in sample_data.iterrows():
            code = str(row[code_col]).strip().strip('"').strip("'").strip('=').strip('"').zfill(6)
            print("code:"+code)
            listing_date = row[date_col]
            
            # 处理上市日期格式
            if isinstance(listing_date, str):
                try:
                    # 尝试不同的日期格式
                    if '/' in listing_date:
                        listing_date = datetime.strptime(listing_date, '%Y/%m/%d')
                    elif '-' in listing_date:
                        listing_date = datetime.strptime(listing_date, '%Y-%m-%d')
                    else:
                        # 尝试其他格式
                        listing_date = pd.to_datetime(listing_date)
                except:
                    # 如果无法解析，使用默认值
                    listing_date = "无法解析"
            elif isinstance(listing_date, pd.Timestamp):
                listing_date = listing_date.to_pydatetime()
            elif isinstance(listing_date, (int, float)):
                # 处理Excel序列号格式
                try:
                    listing_date = pd.to_datetime(listing_date, origin='1899-12-30')
                except:
                    listing_date = "无法解析"
            
            print(f"代码: {code}, 上市日期: {listing_date}")
        
        print(f"\n文件总行数: {len(df)}")
        return True
    
    except Exception as e:
        print(f"测试过程中出错: {e}")
        return False

def main():
    """
    主测试函数
    """
    print("=" * 80)
    print("测试读取 Astock20260405.xls 文件")
    print("=" * 80)
    
    success = test_read_astock_file()
    
    print("=" * 80)
    if success:
        print("测试成功！")
    else:
        print("测试失败！")
    print("=" * 80)

if __name__ == "__main__":
    main()
