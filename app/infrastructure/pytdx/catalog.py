from __future__ import annotations
"""Pytdx 能力目录（对照 https://pytdx-docs.readthedocs.io/zh-cn/latest/ ）。"""


from dataclasses import dataclass
from typing import Literal

PytdxModule = Literal["hq", "exhq", "reader", "finance", "trade", "pool"]


@dataclass(frozen=True)
class PytdxMethodSpec:
    name: str
    summary: str
    params: tuple[str, ...] = ()


def _hq() -> tuple[PytdxMethodSpec, ...]:
    return (
        PytdxMethodSpec("get_security_bars", "K线", ("category", "market", "code", "start", "count")),
        PytdxMethodSpec("get_index_bars", "指数K线", ("category", "market", "code", "start", "count")),
        PytdxMethodSpec("get_security_quotes", "实时行情", ("all_stock", "code")),
        PytdxMethodSpec("get_security_count", "证券数量", ("market",)),
        PytdxMethodSpec("get_security_list", "证券列表", ("market", "start")),
        PytdxMethodSpec("get_minute_time_data", "分时", ("market", "code")),
        PytdxMethodSpec("get_history_minute_time_data", "历史分时", ("market", "code", "date")),
        PytdxMethodSpec("get_transaction_data", "分笔", ("market", "code", "start", "count")),
        PytdxMethodSpec("get_history_transaction_data", "历史分笔", ("market", "code", "start", "count", "date")),
        PytdxMethodSpec("get_company_info_category", "公司信息目录", ("market", "code")),
        PytdxMethodSpec("get_company_info_content", "公司信息内容", ("market", "code", "filename", "start", "length")),
        PytdxMethodSpec("get_xdxr_info", "除权除息", ("market", "code")),
        PytdxMethodSpec("get_finance_info", "财务信息", ("market", "code")),
        PytdxMethodSpec("get_block_info_meta", "板块元信息", ("blockfile",)),
        PytdxMethodSpec("get_block_info", "板块数据块", ("blockfile", "start", "size")),
        PytdxMethodSpec("get_and_parse_block_info", "解析板块", ("blockfile",)),
        PytdxMethodSpec("get_report_file", "调研报告文件", ("filename", "offset")),
        PytdxMethodSpec("get_report_file_by_size", "调研报告(按大小)", ("filename", "filesize", "reporthook")),
        PytdxMethodSpec("get_k_data", "日K(便捷)", ("code", "start_date", "end_date")),
        PytdxMethodSpec("do_heartbeat", "心跳", ()),
    )


def _exhq() -> tuple[PytdxMethodSpec, ...]:
    return (
        PytdxMethodSpec("get_markets", "市场列表", ()),
        PytdxMethodSpec("get_instrument_count", "合约数量", ()),
        PytdxMethodSpec("get_instrument_quote", "合约行情", ("market", "code")),
        PytdxMethodSpec("get_instrument_bars", "合约K线", ("category", "market", "code", "start", "count")),
        PytdxMethodSpec("get_minute_time_data", "分时", ("market", "code")),
        PytdxMethodSpec("get_history_minute_time_data", "历史分时", ("market", "code", "date")),
        PytdxMethodSpec("get_transaction_data", "分笔", ("market", "code", "start", "count")),
        PytdxMethodSpec("get_history_transaction_data", "历史分笔", ("market", "code", "date", "start", "count")),
        PytdxMethodSpec("get_history_instrument_bars_range", "历史K线区间", ("market", "code", "start", "end")),
        PytdxMethodSpec("get_instrument_info", "合约信息", ("start", "count")),
        PytdxMethodSpec("get_instrument_quote_list", "合约行情列表", ("market", "category", "start", "count")),
        PytdxMethodSpec("do_heartbeat", "心跳", ()),
    )


def _reader() -> tuple[PytdxMethodSpec, ...]:
    return (
        PytdxMethodSpec("read_daily", "日K文件", ("symbol", "market")),
        PytdxMethodSpec("read_minute", "分钟线", ("symbol", "market")),
        PytdxMethodSpec("read_lc_minute", "LC分钟线", ("symbol", "market")),
        PytdxMethodSpec("read_exhq_daily", "扩展行情日K", ("market", "code")),
        PytdxMethodSpec("read_gbbq", "股本变迁", ()),
        PytdxMethodSpec("read_block", "板块文件", ("block_file",)),
        PytdxMethodSpec("read_customer_block", "自定义板块", ("block_file",)),
        PytdxMethodSpec("read_history_financial", "历史财务文件", ("filepath",)),
    )


def _finance() -> tuple[PytdxMethodSpec, ...]:
    return (
        PytdxMethodSpec("get_finance_info", "在线财务", ("market", "code")),
        PytdxMethodSpec("crawl_history_financial_list", "历史财务列表爬取", ()),
        PytdxMethodSpec("crawl_history_financial_file", "下载历史财务文件", ("filename", "dest_dir")),
        PytdxMethodSpec("parse_history_financial", "解析历史财务", ("filepath",)),
    )


def _trade() -> tuple[PytdxMethodSpec, ...]:
    return (
        PytdxMethodSpec("ping", "探测交易服务", ()),
        PytdxMethodSpec("logon", "登录", ("ip", "port", "version", "yyb_id", "account_id", "trade_account", "jy_passwrod", "tx_password")),
        PytdxMethodSpec("logoff", "登出", ("client_id",)),
        PytdxMethodSpec("query_data", "查询", ("client_id", "category")),
        PytdxMethodSpec("send_order", "下单", ("client_id", "category", "price_type", "gddm", "zqdm", "price", "quantity")),
        PytdxMethodSpec("cancel_order", "撤单", ("client_id", "exchange_id", "hth")),
        PytdxMethodSpec("get_quote", "行情", ("client_id", "code")),
        PytdxMethodSpec("get_quotes", "批量行情", ("client_id", "codes")),
        PytdxMethodSpec("repay", "还款", ("client_id", "amount")),
        PytdxMethodSpec("query_history_data", "历史查询", ("client_id", "category", "begin_date", "end_date")),
        PytdxMethodSpec("query_datas", "批量查询", ("client_id", "categories")),
        PytdxMethodSpec("send_orders", "批量下单", ("client_id", "orders")),
        PytdxMethodSpec("cancel_orders", "批量撤单", ("client_id", "orders")),
        PytdxMethodSpec("get_active_clients", "活跃客户端", ()),
        PytdxMethodSpec("call", "原始 RPC", ("func", "params")),
    )


def _pool() -> tuple[PytdxMethodSpec, ...]:
    return (
        PytdxMethodSpec("init_pool", "初始化连接池", ("servers",)),
        PytdxMethodSpec("pool_status", "连接池状态", ()),
    ) + _hq()


PYTDX_CATALOG: dict[PytdxModule, tuple[PytdxMethodSpec, ...]] = {
    "hq": _hq(),
    "exhq": _exhq(),
    "reader": _reader(),
    "finance": _finance(),
    "trade": _trade(),
    "pool": _pool(),
}


def allowed_methods(module: PytdxModule) -> frozenset[str]:
    return frozenset(m.name for m in PYTDX_CATALOG[module])


def catalog_to_dict() -> dict[str, list[dict[str, object]]]:
    out: dict[str, list[dict[str, object]]] = {}
    for mod, specs in PYTDX_CATALOG.items():
        out[mod] = [
            {"name": s.name, "summary": s.summary, "params": list(s.params)}
            for s in specs
        ]
    return out
