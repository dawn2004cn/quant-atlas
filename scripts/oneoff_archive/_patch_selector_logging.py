"""One-off: migrate scripts/*_selector.py print() to selector_logging."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKIP = {"stochastic_selector.py", "test_short_selector.py", "selector_logging.py"}
FILES = sorted(p for p in ROOT.glob("*_selector.py") if p.name not in SKIP)

IMPORT_BLOCK = (
    "from selector_logging import get_selector_logger\n\n"
    "logger = get_selector_logger(__name__)\n"
)

REPLACEMENTS: list[tuple[str, str]] = [
    (
        r'print\(f"从market_all_cache获取到 \{len\(all_stocks\)\} 只原始股票数据"\)',
        'logger.info("从 market_all_cache 获取到 %s 只原始股票数据", len(all_stocks))',
    ),
    (
        r'print\("缓存中没有全市场数据，尝试从 stocks 表获取\.\.\."\)',
        'logger.info("缓存中没有全市场数据，尝试从 stocks 表获取...")',
    ),
    (
        r'print\(f"从stocks表获取到 \{len\(all_stocks\)\} 只原始股票数据"\)',
        'logger.info("从 stocks 表获取到 %s 只原始股票数据", len(all_stocks))',
    ),
    (
        r'print\("没有获取到任何股票数据，使用默认股票列表"\)',
        'logger.warning("没有获取到任何股票数据，使用默认股票列表")',
    ),
    (
        r'print\(f"使用默认股票列表，共 \{len\(all_stocks\)\} 只股票"\)',
        'logger.info("使用默认股票列表，共 %s 只股票", len(all_stocks))',
    ),
    (
        r'print\(f"从\{market_name\}加载了 \{len\(final_stocks\)\} 只股票，排除了 \{st_count\} 只ST股"\)',
        'logger.info("从 %s 加载了 %s 只股票，排除了 %s 只 ST 股", market_name, len(final_stocks), st_count)',
    ),
    (
        r'print\(f"加载股票列表失败: \{e\}"\)\s*\n\s*import traceback\s*\n\s*traceback\.print_exc\(\)',
        'logger.exception("加载股票列表失败: %s", e)',
    ),
    (
        r'print\(f"发生异常，返回默认股票列表: \{default_stocks\}"\)',
        'logger.warning("发生异常，返回默认股票列表: %s", default_stocks)',
    ),
    (
        r'print\(f"从缓存获取 \{code\} 评分: \{cached_score\[\'score\'\]:\.1f\}分"\)',
        'logger.debug("从缓存获取 %s 评分: %.1f 分", code, cached_score["score"])',
    ),
    (
        r'print\(f"重新计算 \{code\} 评分 \(([^)]+)\)"\)',
        r'logger.debug("重新计算 %s 评分 (\1)", code)',
    ),
    (
        r'print\(f"从缓存获取 \{code\} 历史数据: \{len\(history_data\)\} 条"\)',
        'logger.debug("从缓存获取 %s 历史数据: %s 条", code, len(history_data))',
    ),
    (
        r'print\(f"从线上获取 \{code\} 历史数据"\)',
        'logger.debug("从线上获取 %s 历史数据", code)',
    ),
    (
        r'print\(f"股票 \{code\} 历史数据不足"\)',
        'logger.warning("股票 %s 历史数据不足", code)',
    ),
    (
        r'print\(f"股票 \{code\} 基本信息缺失"\)',
        'logger.warning("股票 %s 基本信息缺失", code)',
    ),
    (
        r'print\(f"股票 \{code\} 价格无效: \{current_price\}"\)',
        'logger.warning("股票 %s 价格无效: %s", code, current_price)',
    ),
    (
        r'print\(f"分析股票 \{code\} 时出错: \{e\}"\)\s*\n\s*import traceback\s*\n\s*traceback\.print_exc\(\)',
        'logger.exception("分析股票 %s 时出错: %s", code, e)',
    ),
    (
        r'print\(f"从缓存获取当天选股报告: \{today\}"\)',
        'logger.info("从缓存获取当天选股报告: %s", today)',
    ),
    (
        r'print\(f"重新生成当天选股报告: \{today\} \(市场: \{market\}, 策略: ([^)]+)\)"\)',
        r'logger.info("重新生成当天选股报告: %s (市场: %s, 策略: \1)", today, market)',
    ),
    (
        r'print\("没有加载到股票列表"\)',
        'logger.warning("没有加载到股票列表")',
    ),
    (
        r'print\(f"开始分析 \{len\(watchlist\)\} 只股票\.\.\."\)',
        'logger.info("开始分析 %s 只股票...", len(watchlist))',
    ),
    (
        r'print\(f"使用 \{max_workers\} 个线程并行分析"\)',
        'logger.info("使用 %s 个线程并行分析", max_workers)',
    ),
    (
        r'print\(f"分析 \{code\} 时出错: \{e\}"\)',
        'logger.warning("分析 %s 时出错: %s", code, e, exc_info=True)',
    ),
    (
        r'print\(f"已分析 \{i \+ 1\}/\{len\(watchlist\)\} 只股票，成功: \{success_count\}, 失败: \{fail_count\}"\)',
        'logger.info("已分析 %s/%s 只股票，成功: %s, 失败: %s", i + 1, len(watchlist), success_count, fail_count)',
    ),
    (
        r'print\(f"分析完成: 成功 \{success_count\} 只, 失败: \{fail_count\} 只"\)',
        'logger.info("分析完成: 成功 %s 只, 失败: %s 只", success_count, fail_count)',
    ),
    (
        r'print\(f"返回评分最高的 \{len\(top_results\)\} 只股票 \(([^)]+)\)"\)',
        r'logger.info("返回评分最高的 %s 只股票 (\1)", len(top_results))',
    ),
    (
        r'print\(f"  - \{stock\[\'name\'\]\}\(\{stock\[\'code\'\]\}\): \{stock\[\'score\'\]\}分, 评级: \{stock\[\'rating\'\]\}, 推荐: \{stock\[\'recommend\'\]\}"\)',
        'logger.info("  - %s(%s): %s 分, 评级: %s, 推荐: %s", stock["name"], stock["code"], stock["score"], stock["rating"], stock["recommend"])',
    ),
    (
        r'print\(f"已保存当天选股报告: \{today\}"\)',
        'logger.info("已保存当天选股报告: %s", today)',
    ),
    (r"print\(report\)", 'logger.info("\\n%s", report)'),
]


def main() -> None:
    for path in FILES:
        text = path.read_text(encoding="utf-8")
        if "get_selector_logger" in text or "print(" not in text:
            continue
        match = re.search(r"\n\nclass ", text)
        if not match:
            print("skip (no class):", path.name)
            continue
        text = text[: match.start()] + "\n" + IMPORT_BLOCK + text[match.start() :]
        for pattern, repl in REPLACEMENTS:
            text = re.sub(pattern, repl, text, flags=re.MULTILINE)
        path.write_text(text, encoding="utf-8")
        remaining = text.count("print(")
        print(f"updated {path.name}, remaining print(): {remaining}")


if __name__ == "__main__":
    main()
