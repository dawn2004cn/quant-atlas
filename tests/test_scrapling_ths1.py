import time
import random
import json
import re
import csv
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup


def crawl_all_with_pure_browser():
    total_pages = 104
    all_combined_data = []
    headers_list = []

    print("🌐 正在启动工业级常驻 Chromium 浏览器...")

    with sync_playwright() as p:
        # 1. 启动一个真实的无头浏览器
        browser = p.chromium.launch(headless=True)

        # 2. 建立一个高仿真的浏览器上下文
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080},
            locale="zh-CN",
            timezone_id="Asia/Shanghai"
        )
        page = context.new_page()

        # 先正常访问一次宿主主页，让浏览器拿到合法的初始 Cookie 和 Session
        print("🏠 正在进行首页握手初始化...")
        page.goto("https://data.10jqka.com.cn/funds/ggzjl/", wait_until="commit", timeout=20000)
        time.sleep(3)

        print(f"\n🚀 开始全量常驻抓取，目标: {total_pages} 页")

        for page_num in range(1, total_pages + 1):
            ajax_url = f"https://data.10jqka.com.cn/funds/ggzjl/field/zdf/order/desc/page/{page_num}/ajax/1/free/1/"

            # --- 引入原地重试逻辑 ---
            max_retries = 3
            success = False

            for attempt in range(1, max_retries + 1):
                print(f"正在抓取第 {page_num}/{total_pages} 页 (尝试 {attempt}/{max_retries})... ", end="", flush=True)

                try:
                    response = page.goto(ajax_url, wait_until="commit", timeout=20000)
                    status = response.status if response else 0

                    if status == 200:
                        html_content = page.content()
                        soup = BeautifulSoup(html_content, "lxml")
                        table = soup.find("table")

                        if table:
                            # 提取表头
                            if not headers_list:
                                thead = table.find("thead")
                                th_tags = thead.find_all("th") if thead else table.find_all("tr")[0].find_all("th")
                                headers_list = [th.text.strip() for th in th_tags]

                            # 提取数据
                            tbody = table.find("tbody")
                            rows = tbody.find_all("tr") if tbody else table.find_all("tr")[1:]

                            page_count = 0
                            for row in rows:
                                cells = row.find_all("td")
                                if not cells:
                                    continue
                                row_data = {headers_list[index]: re.sub(r'\s+', '', cell.text.strip()) for index, cell
                                            in enumerate(cells) if index < len(headers_list)}
                                if row_data:
                                    all_combined_data.append(row_data)
                                    page_count += 1

                            print(f"成功解析 {page_count} 条。 (当前累计: {len(all_combined_data)} 条)")
                            success = True
                            break  # 抓取成功，跳出重试循环，进入下一页
                        else:
                            if "验证码" in html_content or "安全频道" in html_content:
                                print("❌ 遭遇验证码拦截墙！", end="")
                            else:
                                print("未找到表格结构。", end="")
                    else:
                        print(f"失败 (状态码: {status})。 ", end="")

                except Exception as e:
                    print(f"异常: {e}。 ", end="")

                # 如果走到这里说明当前尝试失败了，加大惩罚性等待时间，然后进行下一次重试
                cool_down = 15 * attempt  # 第一次失败歇15秒，第二次歇30秒
                print(f"⚠️ 触发风控，原地冷却 {cool_down} 秒后重试...")
                time.sleep(cool_down)

            # 如果连续重试了 max_retries 次依然失败，再考虑跳过或终止
            if not success:
                print(f"🚨 第 {page_num} 页连续 {max_retries} 次抓取失败，为保程序稳定，跳过此页。")
                continue

            # --- 正常的页际随机休眠 ---
            sleep_time = random.uniform(3.5, 6.0)
            if page_num % 10 == 0:
                sleep_time += random.uniform(10.0, 15.0)
                print(f"☕ 已连续读取 {page_num} 页，深度规避中，休眠 {sleep_time:.1f} 秒...")
            time.sleep(sleep_time)

        browser.close()

    # --- 保存数据 ---
    if all_combined_data:
        print(f"\n🎉 突破重围！共抓取到 {len(all_combined_data)} 条全量数据。")
        with open("all_stock_funds_browser.json", "w", encoding="utf-8") as f:
            json.dump(all_combined_data, f, ensure_ascii=False, indent=4)
        with open("all_stock_funds_browser.csv", "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=headers_list)
            writer.writeheader()
            writer.writerows(all_combined_data)
        print("💾 数据已存入 'all_stock_funds_browser.csv'")
    else:
        print("\n⚠️ 未收集到有效数据。")


if __name__ == "__main__":
    crawl_all_with_pure_browser()