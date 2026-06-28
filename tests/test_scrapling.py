
import time
import random
import json
import re
import csv
import requests
from bs4 import BeautifulSoup
import time
from playwright.sync_api import sync_playwright


def get_dynamic_v_token():
    url = "https://data.10jqka.com.cn/funds/ggzjl/"

    with sync_playwright() as p:
        # 启动 Chromium 浏览器
        browser = p.chromium.launch(headless=True)
        # 伪造标准的浏览器上下文，避免被识别为自动化工具
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080}
        )
        page = context.new_page()

        print("正在拉起无头浏览器请求同花顺...")
        # wait_until="commit" 意思是只要服务器返回了数据就介入，不要等整个 DOM 完全加载
        # 因为同花顺完整的 DOM 加载里包含反调试死循环，会卡死浏览器
        page.goto(url, wait_until="commit")

        # 适当等待 2 秒，让本地的 v.js 脚本有时间在后台执行并写入 Cookie
        time.sleep(2)

        # 获取当前域名下的所有 Cookies
        cookies = context.cookies()

        # 闭合浏览器
        browser.close()

        # 提取 v 值
        v_token = None
        for cookie in cookies:
            if cookie['name'] == 'v':
                v_token = cookie['value']
                break

        if v_token:
            print(f"🎉 动态获取 Hexin-V 成功: {v_token}")
            return f"v={v_token};"
        else:
            print("❌ 未能在 Cookie 中找到 v 值")
            return None

def crawl_all_10jqka_pages():
    # 填入你从浏览器中获取的最新有效 Cookie (最重要的是 v=xxx 这一段)
    MY_COOKIE = "v=A0prLp5iFMTGHphoP2X3Z0f8mzvpO86VwL9COdSD9h0oh-TlvMsepZBPkkin"
    cookie_str = get_dynamic_v_token()
    MY_COOKIE = "v="+cookie_str;
    # 基本请求头
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Referer": "https://data.10jqka.com.cn/funds/ggzjl/",
        "Cookie": MY_COOKIE,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9"
    }

    total_pages = 104
    all_combined_data = []
    headers_list = []  # 用于记录表头

    print(f"🚀 开始全量抓取任务，目标总页数: {total_pages} 页")

    for page_num in range(1, total_pages + 1):
        # 动态构造带有页码的 AJAX 接口 URL
        url = f"https://data.10jqka.com.cn/funds/ggzjl/field/zdf/order/desc/page/{page_num}/ajax/1/free/1/"

        print(f"正在抓取第 {page_num}/{total_pages} 页... ", end="", flush=True)

        try:
            response = requests.get(url, headers=headers, timeout=15)

            if response.status_code == 401 or response.status_code == 403:
                print(
                    f"\n❌ 遭遇阻断 (状态码: {response.status_code})。你的密文 'v' 可能过期了，请去浏览器刷新并更换 Cookie！")
                break

            if response.status_code != 200:
                print(f"失败 (状态码: {response.status_code})，跳过该页。")
                continue

            soup = BeautifulSoup(response.text, "lxml")
            table = soup.find("table")

            if not table:
                print("未找到表格（可能触发了滑动验证码），终止抓取，请检查返回内容。")
                break

            # 如果是第一页，提取一次标准表头
            if not headers_list:
                thead = table.find("thead")
                th_tags = thead.find_all("th") if thead else table.find_all("tr")[0].find_all("th")
                headers_list = [th.text.strip() for th in th_tags]

            # 提取当前页的数据行
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
                        val = re.sub(r'\s+', '', cell.text.strip())
                        row_data[headers_list[index]] = val

                if row_data:
                    all_combined_data.append(row_data)
                    page_count += 1

            print(f"成功成功解析 {page_count} 条。 (当前累计: {len(all_combined_data)} 条)")

            # --- 核心防封控策略 ---
            # 1. 基础随机休眠：每页抓完休息 2 到 4 秒
            sleep_time = random.uniform(2.0, 4.0)

            # 2. 阶梯大休眠：每抓完 15 页，额外多休息 8 秒，让服务器回血
            if page_num % 15 == 0:
                sleep_time += 8.0
                print(f"☕ 已连续抓取 {page_num} 页，触发安全机制，深度休眠 {sleep_time:.1f} 秒...")

            time.sleep(sleep_time)

        except Exception as e:
            print(f"请求发生异常: {e}")
            time.sleep(5)
            continue

    # --- 保存最终数据 ---
    if all_combined_data:
        print(f"\n🎉 抓取结束！共成功收集到 {len(all_combined_data)} 条股票资金数据。")

        # 1. 保存为明文 JSON 备份
        with open("all_stock_funds.json", "w", encoding="utf-8") as f:
            json.dump(all_combined_data, f, ensure_ascii=False, indent=4)

        # 2. 保存为方便量化直接读取的 CSV 文件
        with open("all_stock_funds.csv", "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=headers_list)
            writer.writeheader()
            writer.writerows(all_combined_data)

        print("💾 数据已成功持久化至本地：'all_stock_funds.json' & 'all_stock_funds.csv'")
    else:
        print("\n⚠️ 未能抓取到任何数据，请检查 Cookie 状态。")


if __name__ == "__main__":
    crawl_all_10jqka_pages()