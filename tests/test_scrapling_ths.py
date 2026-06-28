import time
import random
import json
import re
import csv
import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright


def get_dynamic_v_token():
    """
    利用 Playwright 启动无头浏览器，模拟真实访问，
    从而让同花顺前端的 v.js 自动计算并释放最新的 Hexin-V 密文。
    """
    url = "https://data.10jqka.com.cn/funds/ggzjl/"
    print("🌐 [Token 发生器] 正在启动 Chromium 隐身浏览器...")

    try:
        with sync_playwright() as p:
            # 启动无头浏览器
            browser = p.chromium.launch(headless=True)
            # 注入标准的真实浏览器 User-Agent，规避自动化检测
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                viewport={"width": 1920, "height": 1080}
            )
            page = context.new_page()

            # 使用 'commit' 策略：服务器开始返回数据即介入，避开同花顺深层的反调试死循环
            page.goto(url, wait_until="commit", timeout=15000)

            # 稍等 2 秒，给同花顺本地 JS 脚本计算并写入 Cookie 的时间
            time.sleep(2)

            # 提取当前上下文中的所有 Cookie
            cookies = context.cookies()
            browser.close()

            # 筛选出核心的 'v' 参数
            for cookie in cookies:
                if cookie['name'] == 'v':
                    token = cookie['value']
                    print(f"🔑 [Token 发生器] 成功截获最新 Hexin-V 密文: {token[:15]}...")
                    return f"v={token};"

            print("⚠️ [Token 发生器] 未能在 Cookie 中筛选到 'v' 参数。")
            return None
    except Exception as e:
        print(f"❌ [Token 发生器] 浏览器运行异常: {e}")
        return None


def crawl_all_10jqka_data():
    """
    主爬虫程序：自动获取 Token 并在 HTTP 请求中复用，遍历抓取 104 页全量数据
    """
    # 1. 动态获取核心 Cookie
    dynamic_cookie = get_dynamic_v_token()
    if not dynamic_cookie:
        print("🚨 动态 Token 获取失败，程序终止。请检查网络或环境依赖。")
        return

    # 2. 构造基础请求头
    base_headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Referer": "https://data.10jqka.com.cn/funds/ggzjl/",
        "Cookie": dynamic_cookie,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9"
    }

    total_pages = 104
    all_combined_data = []
    headers_list = []  # 用于动态记录和比对表头

    print(f"\n🚀 全量抓取任务正式启动，目标总页数: {total_pages} 页")

    for page_num in range(1, total_pages + 1):
        sleep_time(2)
        # 拼接目标 AJAX 数据接口
        url = f"https://data.10jqka.com.cn/funds/ggzjl/field/zdf/order/desc/page/{page_num}/ajax/1/free/1/"

        print(f"正在抓取第 {page_num}/{total_pages} 页... ", end="", flush=True)

        try:
            # 直接使用 requests 发送极轻量级的 HTTP GET 请求
            response = requests.get(url, headers=base_headers, timeout=15)

            # 如果中途判定密文失效（通常不会，因为104页只需几分钟，而Token可持续1小时以上）
            if response.status_code in [401, 403]:
                print(f"\n⚠️ 密文临时失效 (状态码: {response.status_code})，正在重新唤醒浏览器补签...")
                dynamic_cookie = get_dynamic_v_token()
                if not dynamic_cookie:
                    print("🚨 补签失败，被迫中断。")
                    break
                base_headers["Cookie"] = dynamic_cookie
                # 重新请求当前页
                response = requests.get(url, headers=base_headers, timeout=15)

            if response.status_code != 200:
                print(f"失败 (状态码: {response.status_code})，跳过当前页。")
                continue

            # 解析纯 HTML 片段
            soup = BeautifulSoup(response.text, "lxml")
            table = soup.find("table")

            if not table:
                print("未能在响应中解析到 table 标签，可能触发了滑动验证码风控。")
                break

            # 首页初始化提取标准表头
            if not headers_list:
                thead = table.find("thead")
                th_tags = thead.find_all("th") if thead else table.find_all("tr")[0].find_all("th")
                headers_list = [th.text.strip() for th in th_tags]

            # 提取表格行
            tbody = table.find("tbody")
            rows = tbody.find_all("tr") if tbody else table.find_all("tr")[1:]

            page_count = 0
            for row in rows:
                cells = row.find_all("td")
                if not cells:
                    continue

                row_data = {}
                for index, cell in enumerate(cells):
                    if index < len(headers_list):
                        # 清洗多余换行、空格符
                        val = re.sub(r'\s+', '', cell.text.strip())
                        row_data[headers_list[index]] = val

                if row_data:
                    all_combined_data.append(row_data)
                    page_count += 1

            print(f"成功解析 {page_count} 条。 (当前累计: {len(all_combined_data)} 条)")

            # --- 工业级防封策略 ---
            # 1. 基础随机休眠 (2 ~ 4 秒)
            sleep_time = random.uniform(2.0, 4.0)

            # 2. 阶梯深度休眠：每抓满 15 页，额外多休息 6 秒，降低高频访问特征
            if page_num % 15 == 0:
                sleep_time += 6.0
                print(f"☕ 已连续抓取 {page_num} 页，触发安全节流机制，深呼吸 {sleep_time:.1f} 秒...")

            time.sleep(sleep_time)

        except Exception as e:
            print(f"处理第 {page_num} 页时遭遇异常: {e}")
            time.sleep(5)
            continue

    # --- 最终数据持久化 ---
    if all_combined_data:
        print(f"\n🎉 完美收工！全量抓取结束，共成功收集到 {len(all_combined_data)} 条股票资金流向数据。")

        # 1. 保存为标准的 JSON 数据
        with open("all_stock_funds.json", "w", encoding="utf-8") as f:
            json.dump(all_combined_data, f, ensure_ascii=False, indent=4)

        # 2. 保存为方便 Pandas 或大数据库直接读取的 CSV 格式
        with open("all_stock_funds.csv", "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=headers_list)
            writer.writeheader()
            writer.writerows(all_combined_data)

        print("💾 文件已成功持久化至本地：'all_stock_funds.json' 与 'all_stock_funds.csv'")
    else:
        print("\n⚠️ 未获取到有效数据，请检查执行日志。")


if __name__ == "__main__":
    crawl_all_10jqka_data()