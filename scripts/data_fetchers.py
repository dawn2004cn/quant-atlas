#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据获取工具函数
"""

import yfinance as yf
import pandas as pd
import requests
import json
from datetime import datetime

# 尝试导入 adata，如果未安装则忽略
try:
    import adata
    ADATA_AVAILABLE = True
except ImportError:
    ADATA_AVAILABLE = False

# 尝试导入 akshare，如果未安装则忽略
try:
    import akshare as ak
    AKSHARE_AVAILABLE = True
except ImportError:
    AKSHARE_AVAILABLE = False


def get_yahoo_ticker(code: str) -> str:
    """
    获取Yahoo Finance的股票代码格式
    
    Args:
        code: 股票代码
        
    Returns:
        str: Yahoo Finance格式的股票代码
    """
    code = str(code).zfill(6)
    if code.startswith('6'):
        return f"{code}.SS"
    elif code.startswith(('0', '3')):
        return f"{code}.SZ"
    elif code.startswith(('8', '9')):  # 北交所股票代码以8或9开头
        return f"{code}.BJ"
    else:
        return f"{code}.BJ"


def get_tencent_full_code(code: str) -> str:
    """
    获取腾讯接口的股票代码格式
    
    Args:
        code: 股票代码
        
    Returns:
        str: 腾讯接口格式的股票代码
    """
    code = str(code).zfill(6)
    if code.startswith('6'):
        return f"sh{code}"
    elif code.startswith(('0', '3')):
        return f"sz{code}"
    elif code.startswith(('8', '9')):  # 北交所股票代码以8或9开头
        return f"bj{code}"
    else:
        return f"bj{code}"


def get_sohu_code(code: str) -> str:
    """
    获取搜狐接口的股票代码格式
    
    Args:
        code: 股票代码
        
    Returns:
        str: 搜狐接口格式的股票代码
    """
    code = str(code).zfill(6)
    # 搜狐接口对于北交所股票的处理可能不同，尝试使用不同的格式
    if code.startswith(('8', '9')):  # 北交所股票代码以8或9开头
        # 尝试使用不同的格式，先尝试不带前缀
        return f"cn_{code}"
    else:
        return f"cn_{code}"


def fetch_from_yfinance(code: str, start_date: str, end_date: str) -> tuple:
    """
    从Yahoo Finance获取股票数据
    
    Args:
        code: 股票代码
        start_date: 开始日期
        end_date: 结束日期
        
    Returns:
        tuple: (DataFrame, 错误信息)
    """
    try:
        ticker = get_yahoo_ticker(code)
        df = yf.download(
            tickers=ticker,
            start=start_date,
            end=end_date,
            interval="1d",
            auto_adjust=True,
            progress=False,
            timeout=20
        )
        if not df.empty and len(df) > 20:
            # 统一列名为小写
            df = df[['Open', 'High', 'Low', 'Close', 'Volume']]
            df.columns = ['open', 'high', 'low', 'close', 'volume']
            # 确保数据范围正确
            df = df.loc[start_date:end_date]
            print(f"yfinance 返回数据形状: {df.shape}")
            return df, None
        print("code:"+code+",yfinance 返回数据不足或为空")
        return None, "yfinance 数据不足"
    except requests.exceptions.Timeout:
        return None, "yfinance 网络超时"
    except requests.exceptions.ConnectionError:
        return None, "yfinance 连接错误"
    except requests.exceptions.HTTPError as e:
        return None, f"yfinance HTTP错误: {e.response.status_code if e.response else '未知'}"
    except requests.exceptions.RequestException as e:
        return None, f"yfinance 网络异常: {str(e)[:50]}"
    except Exception as e:
        return None, f"yfinance 异常: {str(e)[:80]}"


def fetch_from_tencent(code: str, start_date: str, end_date: str) -> tuple:
    """
    从腾讯接口获取股票数据
    
    Args:
        code: 股票代码
        start_date: 开始日期
        end_date: 结束日期
        
    Returns:
        tuple: (DataFrame, 错误信息)
    """
    session = requests.Session()
    try:
        # 使用更接近示例的URL参数
        url = f"https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?_var=kline_dayqfq&param={get_tencent_full_code(code)},day,{start_date},{end_date},1000,qfqa"
        resp = session.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
        print("code:"+code+"tencent url:"+url)
        resp.raise_for_status()  # 检查HTTP状态码
        text = resp.text.strip()
        if "kline_dayqfq=" in text:
            json_str = text.split("kline_dayqfq=", 1)[1].strip()
            if json_str.endswith(';'):
                json_str = json_str[:-1]
        else:
            json_str = text

        data = json.loads(json_str)
        
        # 处理返回格式
        kline = None
        
        # 检查数据结构
        if isinstance(data, dict):
            # 检查返回状态
            code_value = data.get("code", 1)
            msg = data.get("msg", "")
            if code_value != 0:
                return None, f"腾讯接口错误: {msg}"
            
            # 检查 data 字段
            data_field = data.get("data", {})
            
            # 处理不同的数据结构
            if isinstance(data_field, dict):
                # 标准格式，data 是字典
                full = get_tencent_full_code(code)
                kline = data_field.get(full, {}).get("day")
            elif isinstance(data_field, list):
                # 特殊格式，data 是列表
                if len(data_field) > 0:
                    # 尝试从列表中获取数据
                    for item in data_field:
                        if isinstance(item, dict):
                            # 检查是否有 day 键
                            if "day" in item:
                                kline = item.get("day")
                                if kline:
                                    break
                            # 检查是否有股票代码键
                            full = get_tencent_full_code(code)
                            if full in item:
                                kline = item.get(full, {}).get("day")
                                if kline:
                                    break
        
        if not kline:
            return None, "腾讯无前复权数据"

        # 验证数据格式
        if not isinstance(kline, list) or len(kline) == 0:
            return None, "腾讯返回数据格式错误"

        # 确保数据是列表格式且每个元素也是列表
        if not all(isinstance(item, list) for item in kline):
            print("腾讯返回数据格式错误: kline 数据不是列表格式")
            return None, "腾讯返回数据格式错误"

        df = pd.DataFrame(kline, columns=['date', 'open', 'close', 'high', 'low', 'volume', 'amount'])
        df['date'] = pd.to_datetime(df['date'])
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df[col] = pd.to_numeric(df[col], errors='coerce')

        df.set_index('date', inplace=True)
        df = df[['open', 'high', 'low', 'close', 'volume']]
        df = df.loc[start_date:end_date]
        return df, None
    except requests.exceptions.Timeout:
        return None, "腾讯网络超时"
    except requests.exceptions.ConnectionError:
        return None, "腾讯连接错误"
    except requests.exceptions.HTTPError as e:
        return None, f"腾讯HTTP错误: {e.response.status_code if e.response else '未知'}"
    except requests.exceptions.RequestException as e:
        return None, f"腾讯网络异常: {str(e)[:50]}"
    except json.JSONDecodeError:
        return None, "腾讯返回数据格式错误"
    except Exception as e:
        return None, f"腾讯异常: {str(e)[:80]}"
    finally:
        session.close()


def fetch_from_sohu(code: str, start_date: str, end_date: str) -> tuple:
    """
    从搜狐接口获取股票数据
    
    Args:
        code: 股票代码
        start_date: 开始日期
        end_date: 结束日期
        
    Returns:
        tuple: (DataFrame, 错误信息)
    """
    session = requests.Session()
    try:
        sohu_code = get_sohu_code(code)
        # 确保 sohu_code 是字符串且不包含引号
        sohu_code = str(sohu_code).strip().strip('"').strip("'").strip('`')
        
        # 构建 URL，确保参数正确编码
        import urllib.parse
        url = f"https://q.stock.sohu.com/hisHq?code={urllib.parse.quote(sohu_code)}&start={start_date.replace('-', '')}&end={end_date.replace('-', '')}&stat=1&order=D&period=d&rt=json"

        resp = session.get(url, timeout=20, headers={"User-Agent": "Mozilla/5.0"})
        print(f"code:{code} sohu url:{url}")
        resp.raise_for_status()  # 检查HTTP状态码
        data_list = resp.json()

        if not data_list or not isinstance(data_list, list) or len(data_list) == 0:
            print("搜狐返回数据格式错误或数据为空")
            return None, "搜狐返回空数据"

        # 检查返回数据是否包含错误信息
        if isinstance(data_list, list) and len(data_list) > 0:
            first_item = data_list[0]
            if isinstance(first_item, dict):
                # 检查是否有错误信息
                if 'status' in first_item and first_item['status'] != 0:
                    msg = first_item.get('msg', '未知错误')
                    print(f"搜狐返回错误: {msg}")
                    return None, f"搜狐返回错误: {msg}"

        hq = data_list[0].get("hq", [])
        if not hq:
            return None, "搜狐无 hq 数据"

        # 根据搜狐接口返回的数据字段顺序：日期、开盘价、收盘价、涨跌额、涨跌幅、最低价、最高价、成交量、成交额、换手率
        df = pd.DataFrame(hq, columns=['date', 'open', 'close', 'change', 'pct', 'low', 'high', 'volume', 'amount',
                                       'turnover'])
        df['date'] = pd.to_datetime(df['date'])
        for col in ['open', 'high', 'low', 'close', 'volume', 'amount']:
            df[col] = pd.to_numeric(df[col], errors='coerce')

        df.set_index('date', inplace=True)
        
        # 确保时间索引是单调递增的
        df.sort_index(inplace=True)
        
        df = df[['open', 'high', 'low', 'close', 'volume']]
        
        # 安全地进行时间范围过滤
        try:
            df = df.loc[start_date:end_date]
        except Exception as e:
            print(f"搜狐接口时间范围过滤失败: {str(e)}")
            # 如果过滤失败，返回所有数据
            pass
        
        return df, None
    except requests.exceptions.Timeout:
        return None, "搜狐网络超时"
    except requests.exceptions.ConnectionError:
        return None, "搜狐连接错误"
    except requests.exceptions.HTTPError as e:
        return None, f"搜狐HTTP错误: {e.response.status_code if e.response else '未知'}"
    except requests.exceptions.RequestException as e:
        return None, f"搜狐网络异常: {str(e)[:50]}"
    except json.JSONDecodeError:
        return None, "搜狐返回数据格式错误"
    except Exception as e:
        return None, f"搜狐异常: {str(e)[:80]}"
    finally:
        session.close()


def fetch_from_adata(code: str, start_date: str, end_date: str) -> tuple:
    """
    从adata获取股票数据
    
    Args:
        code: 股票代码
        start_date: 开始日期
        end_date: 结束日期
        
    Returns:
        tuple: (DataFrame, 错误信息)
    """
    if not ADATA_AVAILABLE:
        return None, "adata 库未安装"
    
    try:
        # 确保股票代码格式正确
        code = str(code).zfill(6)
        
        # 对于北交所股票，尝试添加市场标识
        if code.startswith(('8', '9')):  # 北交所股票代码以8或9开头
            # 尝试使用 bj 前缀
            try:
                df = adata.stock.market.get_market(
                    stock_code=f"bj{code}",
                    k_type=1,           # 1=daily
                    start_date=start_date,
                    adjust_type=1        # 1=forward adjusted
                )
                if not df.empty and len(df) >= 20:
                    # 重命名列以匹配项目格式
                    df = df.rename(columns={
                        'trade_date': 'date',
                        'open': 'open',
                        'close': 'close',
                        'high': 'high',
                        'low': 'low',
                        'volume': 'volume'
                    })
                    
                    # 转换日期格式
                    df['date'] = pd.to_datetime(df['date'])
                    df.set_index('date', inplace=True)
                    
                    # 选择需要的列
                    df = df[['open', 'high', 'low', 'close', 'volume']]
                    
                    # 确保数据范围正确
                    df = df.loc[start_date:end_date]
                    
                    return df, None
            except:
                # 如果失败，尝试使用原始代码
                pass
        
        # 使用原始代码获取数据
        df = adata.stock.market.get_market(
            stock_code=code,
            k_type=1,           # 1=daily
            start_date=start_date,
            adjust_type=1        # 1=forward adjusted
        )
        
        if df.empty or len(df) < 20:
            print("code:"+code+",adata is not data")
            return None, "adata 数据不足"
        
        # 重命名列以匹配项目格式
        df = df.rename(columns={
            'trade_date': 'date',
            'open': 'open',
            'close': 'close',
            'high': 'high',
            'low': 'low',
            'volume': 'volume'
        })
        
        # 转换日期格式
        df['date'] = pd.to_datetime(df['date'])
        df.set_index('date', inplace=True)
        
        # 选择需要的列
        df = df[['open', 'high', 'low', 'close', 'volume']]
        
        # 确保数据范围正确
        df = df.loc[start_date:end_date]
        
        return df, None
    except Exception as e:
        return None, f"adata 异常: {str(e)[:80]}"


def fetch_from_akshare(code: str, start_date: str, end_date: str) -> tuple:
    """
    从akshare获取股票数据
    
    Args:
        code: 股票代码
        start_date: 开始日期
        end_date: 结束日期
        
    Returns:
        tuple: (DataFrame, 错误信息)
    """
    if not AKSHARE_AVAILABLE:
        return None, "akshare 库未安装"
    
    try:
        # 确保股票代码格式正确
        code = str(code).zfill(6)
        
        # 确定股票市场
        if code.startswith('6'):
            market = 'sh'
        elif code.startswith(('0', '3')):
            market = 'sz'
        elif code.startswith(('8', '9')):  # 北交所股票
            market = 'bj'
        else:
            market = 'sh'
        
        # 构建 akshare 股票代码
        ak_code = f"{market}{code}"
        
        # 获取股票数据
        df = ak.stock_zh_a_hist(
            symbol=ak_code,
            period="daily",
            start_date=start_date,
            end_date=end_date,
            adjust="qfq"  # 前复权
        )
        
        if df.empty or len(df) < 20:
            print(f"code:{code},akshare is not data")
            return None, "akshare 数据不足"
        
        # 重命名列以匹配项目格式
        df = df.rename(columns={
            '日期': 'date',
            '开盘': 'open',
            '收盘': 'close',
            '最高': 'high',
            '最低': 'low',
            '成交量': 'volume'
        })
        
        # 转换日期格式
        df['date'] = pd.to_datetime(df['date'])
        df.set_index('date', inplace=True)
        
        # 选择需要的列
        df = df[['open', 'high', 'low', 'close', 'volume']]
        
        # 确保数据范围正确
        df = df.loc[start_date:end_date]
        
        return df, None
    except Exception as e:
        return None, f"akshare 异常: {str(e)[:80]}"
