import time
import random
import json
import re
import csv
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup


def crawl_by_clicking_next_page():
    total_pages = 104
    all_combined_data = []
    headers_list = []

    print("🌐 正在启动【极限去特征 + 自动激活模式】仿真浏览器...")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            viewport={"width": 1400, "height": 900},
            locale="zh-CN",
            java_script_enabled=True,
            bypass_csp=True
        )
        page = context.new_page()

        # 抹除自动化特征
        page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            window.chrome = { runtime: {} };
        """)

        print("🏠 正在加载同花顺资金流向首页...")
        page.goto("https://data.10jqka.com.cn/funds/ggzjl/", wait_until="commit")

        print("⏳ 正在等待基础页面渲染...")
        time.sleep(5)

        # 🎯 【核心突破】强行模拟点击一次页面上的“个股资金流向”或者表格排序，激活数据流！
        try:
            print("⚡ 正在自动点击‘个股资金流向’选项卡以激活数据...")
            # 尝试通过文本直接定位并点击该按钮
            active_tab = page.locator("a:has-text('个股资金流向')").first
            if active_tab.is_visible():
                active_tab.click()
            else:
                # 如果没找到，退而求其次，点击一下表格的任意表头（比如排序）来强行刷新表格
                page.locator("th:has-text('最新价')").first.click()
            time.sleep(4)
        except Exception as e:
            print(f"⚠️ 自动激活点击未触发(可能已默认激活): {e}")

        print(f"\n🚀 开始模拟翻页抓取，目标: {total_pages} 页")

        for page_num in range(1, total_pages + 1):
            max_retries = 3
            success = False

            for attempt in range(1, max_retries + 1):
                print(f"当前正在提取第 {page_num}/{total_pages} 页... ", end="", flush=True)

                try:
                    # 如果不是第一页，模拟点击“下一页”
                    if page_num > 1 and attempt == 1:
                        next_btn = page.locator("a:has-text('下一页')")
                        if next_btn.is_visible():
                            next_btn.click()
                            time.sleep(random.uniform(3.0, 4.5))
                        else:
                            print("❌ 未找到'下一页'按钮，可能页面未完全加载。")
                            break

                    html_content = page.content()
                    soup = BeautifulSoup(html_content, "lxml")
                    table = soup.find("table", class_="m-table") or soup.find("table")

                    if table:
                        if not headers_list:
                            thead = table.find("thead")
                            th_tags = thead.find_all("th") if thead else table.find_all("tr")[0].find_all("th")
                            headers_list = [th.text.strip() for th in th_tags]

                        tbody = table.find("tbody")
                        rows = tbody.find_all("tr") if tbody else table.find_all("tr")[1:]

                        page_count = 0
                        for row in rows:
                            cells = row.find_all("td")
                            if not cells:
                                continue
                            row_data = {headers_list[index]: re.sub(r'\s+', '', cell.text.strip()) for index, cell in
                                        enumerate(cells) if index < len(headers_list)}

                            # 过滤并确保抓到的是有效的股票行（比如包含代码）
                            if row_data and any(k for k in ["代码", "股票代码"] if k in row_data):
                                all_combined_data.append(row_data)
                                page_count += 1

                        if page_count > 0:
                            print(f"成功解析 {page_count} 条。 (当前累计: {len(all_combined_data)} 条)")
                            success = True
                            break
                        else:
                            print("表格存在但内容为空，尝试点击表头激活... ", end="")
                            page.locator("th:has-text('最新价')").first.click()
                            time.sleep(3)
                    else:
                        print("未找到表格结构... ", end="")

                except Exception as e:
                    print(f"异常: {e}。 ", end="")

                cool_down = 8 * attempt
                print(f"原地冷却 {cool_down} 秒后重试...")
                time.sleep(cool_down)
                page.reload(wait_until="commit")
                time.sleep(4)

            if not success:
                print(f"🚨 第 {page_num} 页连续失败，跳过。")
                continue

            time.sleep(random.uniform(2.5, 4.0))

        browser.close()

    # --- 保存 ---
    if all_combined_data:
        print(f"\n🎉 大功告成！全量抓取结束，共收集到 {len(all_combined_data)} 条数据。")
        with open("all_stock_funds_click.csv", "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=headers_list)
            writer.writeheader()
            writer.writerows(all_combined_data)
        print("💾 数据已成功存入 'all_stock_funds_click.csv'")


if __name__ == "__main__":
    crawl_by_clicking_next_page()