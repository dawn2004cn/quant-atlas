import yfinance as yf
import requests
import json
import time
from datetime import datetime

# 配置参数
START_DATE = "2023-01-01"
END_DATE = datetime.today().strftime('%Y-%m-%d')

# 测试股票代码
TEST_CODES = ["600000", "600519", "000001", "300001"]

# 辅助函数
def get_yahoo_ticker(code: str) -> str:
    code = str(code).zfill(6)
    if code.startswith('6'):
        return f"{code}.SS"
    elif code.startswith(('0', '3')):
        return f"{code}.SZ"
    else:
        return f"{code}.BJ"

def get_tencent_full_code(code: str) -> str:
    code = str(code).zfill(6)
    if code.startswith('6'):
        return f"sh{code}"
    elif code.startswith(('0', '3')):
        return f"sz{code}"
    else:
        return f"bj{code}"

def get_sohu_code(code: str) -> str:
    return f"cn_{str(code).zfill(6)}"

# 测试 yfinance 接口
def test_yfinance():
    print("\n=== 测试 yfinance 接口 ===")
    for code in TEST_CODES:
        try:
            ticker = get_yahoo_ticker(code)
            start_time = time.time()
            df = yf.download(
                tickers=ticker,
                start=START_DATE,
                end=END_DATE,
                interval="1d",
                auto_adjust=True,
                progress=False,
                timeout=20
            )
            end_time = time.time()
            if not df.empty and len(df) > 10:
                print(f"  ✓ {code} ({ticker}): 成功，数据条数: {len(df)}, 耗时: {end_time - start_time:.2f}s")
            else:
                print(f"  ✗ {code} ({ticker}): 失败，数据不足")
        except Exception as e:
            print(f"  ✗ {code} ({ticker}): 异常 - {str(e)[:50]}")
        time.sleep(1)  # 避免请求过快

# 测试腾讯接口
def test_tencent():
    print("\n=== 测试 腾讯 接口 ===")
    session = requests.Session()
    try:
        for code in TEST_CODES:
            try:
                # 使用正确的URL参数
                url = f"https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?_var=kline_dayqfq&param={get_tencent_full_code(code)},day,,,1000,qfqa"
                start_time = time.time()
                resp = session.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
                resp.raise_for_status()
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
                        print(f"  ✗ {code}: 接口错误 - {msg}")
                        continue
                    
                    # 检查 data 字段
                    data_field = data.get("data", {})
                    
                    # 处理 data 是列表的情况
                    if isinstance(data_field, list):
                        # 检查列表是否为空
                        if len(data_field) > 0:
                            # 尝试从列表中获取数据
                            for item in data_field:
                                if isinstance(item, dict) and "day" in item:
                                    kline = item.get("day")
                                    if kline:
                                        break
                    else:
                        # 直接检查是否有 day 键
                        if "day" in data:
                            kline = data.get("day")
                        else:
                            # 尝试原有的路径
                            full = get_tencent_full_code(code)
                            kline = data_field.get(full, {}).get("day")
                end_time = time.time()
                if kline and len(kline) > 10:
                    print(f"  ✓ {code}: 成功，数据条数: {len(kline)}, 耗时: {end_time - start_time:.2f}s")
                else:
                    print(f"  ✗ {code}: 失败，数据不足")
            except Exception as e:
                print(f"  ✗ {code}: 异常 - {str(e)[:50]}")
            time.sleep(1)  # 避免请求过快
    finally:
        session.close()

# 测试搜狐接口
def test_sohu():
    print("\n=== 测试 搜狐 接口 ===")
    session = requests.Session()
    try:
        for code in TEST_CODES:
            try:
                sohu_code = get_sohu_code(code)
                url = f"https://q.stock.sohu.com/hisHq?code={sohu_code}&start={START_DATE.replace('-', '')}&end={END_DATE.replace('-', '')}&stat=1&order=D&period=d&rt=json"
                start_time = time.time()
                resp = session.get(url, timeout=20, headers={"User-Agent": "Mozilla/5.0"})
                resp.raise_for_status()
                data_list = resp.json()
                end_time = time.time()
                if data_list and isinstance(data_list, list) and len(data_list) > 0:
                    hq = data_list[0].get("hq", [])
                    if hq and len(hq) > 10:
                        print(f"  ✓ {code}: 成功，数据条数: {len(hq)}, 耗时: {end_time - start_time:.2f}s")
                    else:
                        print(f"  ✗ {code}: 失败，数据不足")
                else:
                    print(f"  ✗ {code}: 失败，返回空数据")
            except Exception as e:
                print(f"  ✗ {code}: 异常 - {str(e)[:50]}")
            time.sleep(1)  # 避免请求过快
    finally:
        session.close()

if __name__ == "__main__":
    print("开始测试三种数据源接口可用性...")
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"测试日期范围: {START_DATE} ~ {END_DATE}")
    
    test_yfinance()
    test_tencent()
    test_sohu()
    
    print("\n测试完成！")
