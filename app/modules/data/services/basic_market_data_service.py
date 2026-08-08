from __future__ import annotations
"""龙虎榜 / 研报 / 财报本地快照 入库与查询（AkShare + 可选东方财富 HTML）。"""


import io
import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import pandas as pd
import requests

from app.config import BASE_DIR
from app.core.logger import get_logger
from app.core.runtime_config import get_runtime
from app.core.utils.datetime_utils import norm_date
from app.modules.system.services.helpers.tdx_local_access import get_tdx_local_file_port
from app.domain.shared.tdx_paths import TdxLocalPaths, resolve_tdx_root
from app.modules.system.services.helpers.longhu_mapping_access import get_longhu_mapping_port
from app.domain.dto.market_data_dto import LonghuEntry
from app.application.dto.market_data_dto import YanbaoEntry

from app.domain.ports.market_data_ports import IMarketDataIngestor
from app.domain.shared.eastmoney_parser import EastmoneyParser
from app.core.utils.pandas_utils import json_safe

logger = get_logger(__name__)
from app.domain.ports.repository_ports import IBasicMarketDataRepository

from app.domain.dto.service_result import GenericResponseDTO

class BasicMarketDataService:
    def __init__(
        self,
        *,
        repository: Any = None,
        telemetry: Any = None,
        longhu_adapter: Any = None,
        base_dir: Any = None,
        tdx_root_path: Any = None,
        stock_cache: Any = None,
    ) -> None:
        self._repo = repository
        self._telemetry = telemetry
        self._longhu_adapter = longhu_adapter
        self._base_dir = base_dir
        self._tdx_root_path = tdx_root_path
        self._stock_cache = stock_cache

    @property
    def repository(self) -> IBasicMarketDataRepository:
        return self._repo

    def ingest_longhu_em(self, *, lookback_calendar_days: int = 14) -> GenericResponseDTO:
        """东方财富龙虎榜明细入库（AkShare ``stock_lhb_detail_em``）。"""
        end = datetime.now()
        start = end - timedelta(days=lookback_calendar_days)
        from app.application.request_executor import run_async

        return run_async(self.ingest_longhu_em_between(start, end, update_last_meta=True))

    async def ingest_longhu_em_between(
        self,
        start: datetime,
        end: datetime,
        *,
        update_last_meta: bool = False,
    ) -> GenericResponseDTO:
        """按自然日区间拉取龙虎榜并 upsert。"""
        start_s = start.strftime("%Y%m%d")
        end_s = end.strftime("%Y%m%d")
        
        if self._longhu_adapter is None:
            return {"ok": False, "error": "longhu_adapter_not_configured", "rows": 0, "range": {"start": start_s, "end": end_s}}
        
        df = await self._longhu_adapter.fetch_data(start_s, end_s)
        
        if df is None:
            return {"ok": False, "error": "adapter_fetch_failed", "rows": 0, "range": {"start": start_s, "end": end_s}}

        if df.empty:
            return {"ok": True, "rows": 0, "message": "empty", "range": {"start": start_s, "end": end_s}}

        # Use mapper
        entries = get_longhu_mapping_port().map_dataframe_to_entries(df)

        # Convert DTOs back to dicts for repository consumption for now
        n = self._repo.upsert_longhu_rows([e.model_dump() for e in entries])
        
        if update_last_meta:
            self._repo.set_meta("last_longhu_ingest", json.dumps({"at": datetime.now().isoformat(), "rows": n}))
        
        logger.info("longhu ingest range %s-%s rows=%d", start_s, end_s, n)
        return {"ok": True, "rows": n, "range": {"start": start_s, "end": end_s}}

    def _run_longhu_full_historical_core(
        self,
        *,
        years: int = 3,
        chunk_days: int = 55,
        sleep_sec: float = 0.35,
        meta_kind: str,
    ) -> GenericResponseDTO:
        """按自然日分段拉取龙虎榜并 upsert（不判断是否空库）。"""
        end = datetime.now()
        start = end - timedelta(days=365 * max(1, min(years, 10)))
        total = 0
        windows: list[dict[str, Any]] = []
        cur = start
        delay = max(0.05, float(sleep_sec))
        while cur < end:
            nxt = min(cur + timedelta(days=max(7, chunk_days)), end)
            r = self.ingest_longhu_em_between(cur, nxt, update_last_meta=False)
            windows.append({"start": cur.strftime("%Y%m%d"), "end": nxt.strftime("%Y%m%d"), "result": r})
            if r.get("ok") and r.get("rows"):
                total += int(r["rows"])
            time.sleep(delay)
            cur = nxt
        self._repo.set_meta(
            "last_longhu_full_backfill",
            json.dumps({"at": datetime.now().isoformat(), "total_rows": total, "kind": meta_kind}),
        )
        self._repo.set_meta(
            "last_longhu_ingest",
            json.dumps({"at": datetime.now().isoformat(), "rows": total, "kind": meta_kind}),
        )
        return {"ok": True, "skipped": False, "total_rows": total, "windows": len(windows), "windows_detail": windows[-5:]}

    def run_longhu_full_historical_if_no_stock(
        self,
        *,
        years: int = 3,
        chunk_days: int = 55,
        sleep_sec: float = 0.35,
    ) -> GenericResponseDTO:
        """一次性龙虎榜存量：仅当库中无任何龙虎榜记录时执行，按区间分段拉取。"""
        if self._repo.count_longhu_rows() > 0:
            return {
                "skipped": True,
                "reason": "existing_longhu_data",
                "count": self._repo.count_longhu_rows(),
            }
        return self._run_longhu_full_historical_core(
            years=years,
            chunk_days=chunk_days,
            sleep_sec=sleep_sec,
            meta_kind="full_backfill_if_empty",
        )

    def run_longhu_full_historical_force(
        self,
        *,
        years: int = 3,
        chunk_days: int = 55,
        sleep_sec: float = 0.35,
    ) -> GenericResponseDTO:
        """强制全量龙虎榜：分段拉取并 upsert（与空库回填同逻辑，不跳过已有数据）。"""
        return self._run_longhu_full_historical_core(
            years=years,
            chunk_days=chunk_days,
            sleep_sec=sleep_sec,
            meta_kind="full_backfill_force",
        )

    def run_financial_full_stash_if_empty(
        self,
        *,
        codes: list[str] | None = None,
        sleep_sec: float = 0.35,
    ) -> GenericResponseDTO:
        """一次性财报快照：仅当 ``cn_financial_stash`` 无记录时，按代码列表爬取东财三表摘要入库。"""
        if self._repo.count_financial_stash_rows() > 0:
            return {
                "skipped": True,
                "reason": "existing_financial_stash",
                "count": self._repo.count_financial_stash_rows(),
            }
        default_codes = "600519,000001,300750,601318,000858"
        env_codes = get_runtime("FINANCIAL_FULL_BACKFILL_CODES", "").strip()
        resolved = codes if codes is not None else self._parse_code_list(env_codes or None, default_csv=default_codes)
        if not resolved:
            return {"ok": False, "error": "no_codes", "skipped": False}
        from app.modules.system.services.helpers.cn_fundamentals_access import get_cn_fundamentals_port
        prov = get_cn_fundamentals_port()
        ok_n = 0
        err_n = 0
        for code in resolved:
            try:
                bundle = prov.fetch_financial_bundle(code)
                self._repo.upsert_financial_stash(code, bundle)
                ok_n += 1
            except Exception as exc:  # noqa: BLE001
                logger.warning("financial stash %s: %s", code, exc)
                err_n += 1
            time.sleep(max(0.05, sleep_sec))
        self._repo.set_meta(
            "last_financial_full_backfill",
            json.dumps({"at": datetime.now().isoformat(), "ok": ok_n, "err": err_n}),
        )
        return {"ok": True, "skipped": False, "codes": len(resolved), "ok_n": ok_n, "err_n": err_n}

    @staticmethod
    def _parse_code_list(raw: str | None, *, default_csv: str) -> list[str]:
        from app.domain.shared.symbol_normalizer import SymbolNormalizer
        s = (raw or "").strip() or default_csv
        out: list[str] = []
        for x in s.split(","):
            code = SymbolNormalizer.normalize_code(x)
            if len(code) == 6:
                out.append(code)
        return out

    def refresh_financial_stash_for_codes(self, codes: list[str], *, sleep_sec: float = 0.25) -> GenericResponseDTO:
        """增量：刷新指定代码的财报快照（覆盖 upsert）。"""
        if not codes:
            return {"ok": True, "rows": 0, "message": "no_codes"}
        from app.modules.system.services.helpers.cn_fundamentals_access import get_cn_fundamentals_port
        from app.domain.shared.symbol_normalizer import SymbolNormalizer
        prov = get_cn_fundamentals_port()
        ok_n = 0
        for code in codes:
            c = SymbolNormalizer.normalize_code(code)
            if len(c) != 6:
                continue
            try:
                self._repo.upsert_financial_stash(c, prov.fetch_financial_bundle(c))
                ok_n += 1
            except Exception as exc:  # noqa: BLE001
                logger.warning("financial refresh %s: %s", c, exc)
            time.sleep(max(0.05, sleep_sec))
        self._repo.set_meta("last_financial_refresh", json.dumps({"at": datetime.now().isoformat(), "ok": ok_n}))
        return {"ok": True, "rows": ok_n}

    def ingest_yanbao_eastmoney_html(
        self,
        *,
        categories: dict[str, str] | None = None,
        max_rows_per_category: int = 200,
    ) -> GenericResponseDTO:
        """抓取东方财富研报列表页，写入 ``yanbao_items``。"""
        from app.domain.shared.symbol_normalizer import SymbolNormalizer
        cats = categories or {
            "个股研报": "https://data.eastmoney.com/report/stock.jshtml",
            "行业研报": "https://data.eastmoney.com/report/industry.jshtml",
            "宏观研究": "https://data.eastmoney.com/report/macresearch.jshtml",
            "策略报告": "https://data.eastmoney.com/report/strategyreport.jshtml",
            "券商晨报": "https://data.eastmoney.com/report/brokerreport.jshtml",
            "新股研报": "https://data.eastmoney.com/report/newstock.jshtml"
        }
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": "https://data.eastmoney.com/",
        }
        cap = max(1, min(int(max_rows_per_category), 800))
        batch = datetime.now().strftime("%Y%m%d_%H%M%S")
        total = 0
        errors: list[str] = []
        parser = EastmoneyParser()
        
        for cat_name, url in cats.items():
            try:
                resp = requests.get(url, headers=headers, timeout=20)
                resp.encoding = "utf-8"
                if resp.status_code != 200:
                    errors.append(f"{cat_name}:http{resp.status_code}")
                    continue
                dfs = pd.read_html(io.StringIO(resp.text))
                if not dfs:
                    errors.append(f"{cat_name}:no_table")
                    continue
                df = dfs[0]
                df.columns = [str(c).strip().replace("\n", "") for c in df.columns]
                
                title_c = parser.find_col(df, "标题") or parser.find_col(df, "报告")
                org_c = parser.find_col(df, "机构")
                date_c = parser.find_col(df, "日期")
                code_c = parser.find_col(df, "代码")
                link_c = next((c for c in df.columns if "链接" in str(c) or "href" in str(c).lower()), None)
                
                entries: list[YanbaoEntry] = []
                for _, row in df.head(cap).iterrows():
                    raw_row = {str(k): json_safe(v) for k, v in row.items()}
                    title = str(row.get(title_c) or "")[:512]
                    if not title:
                        continue
                        
                    entries.append(YanbaoEntry(
                        category=cat_name,
                        title=title,
                        org_name=str(row.get(org_c) or "")[:128],
                        pub_date=norm_date(row.get(date_c)),
                        stock_code=SymbolNormalizer.normalize_code(row.get(code_c)),
                        report_url=str(row.get(link_c) or "")[:1024],
                        raw=raw_row
                    ))
                n = self._repo.insert_yanbao_batch(cat_name, [e.model_dump() for e in entries], batch)
                total += n
            except Exception as exc:  # noqa: BLE001
                logger.warning("yanbao %s: %s", cat_name, exc)
                errors.append(f"{cat_name}:{exc!s}")
        
        self._repo.set_meta(
            "last_yanbao_ingest",
            json.dumps({"at": datetime.now().isoformat(), "rows": total, "max_rows_per_category": cap}),
        )
        return {"ok": True, "rows": total, "errors": errors, "max_rows_per_category": cap}

    def ingest_yanbao_eastmoney_api(
        self,
        *,
        begin: str,
        end: str,
        include_types: list[str] | None = None,
        page_size: int = 200,
        max_pages: int = 80,
        sleep_sec: float = 0.25,
    ) -> GenericResponseDTO:
        """东财研报 API：覆盖宏观/策略/晨报/行业/个股。"""
        from app.domain.shared.symbol_normalizer import SymbolNormalizer
        types = include_types or ["industry", "stock", "macro", "strategy", "morning"]
        cap = max(20, min(int(page_size), 200))
        page_cap = max(1, min(int(max_pages), 500))
        delay = max(0.05, min(float(sleep_sec), 5.0))
        batch = datetime.now().strftime("%Y%m%d_%H%M%S")
        parser = EastmoneyParser()

        sess = requests.Session()
        sess.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Referer": "https://data.eastmoney.com/",
            }
        )

        def _emit_items(category: str, payload_items: list[dict[str, Any]]) -> int:
            entries: list[YanbaoEntry] = []
            for it in payload_items or []:
                raw = {str(k): json_safe(v) for k, v in (it or {}).items()}
                title = str(raw.get("title") or "")[:512]
                if not title:
                    continue
                org = str(raw.get("orgSName") or raw.get("org_name") or "")[:128]
                pub = str(raw.get("publishDate") or raw.get("publish_date") or raw.get("date") or "")[:32]
                code = SymbolNormalizer.normalize_code(raw.get("stockCode") or raw.get("code") or "")
                
                report_url = ""
                if raw.get("encodeUrl"):
                    pref = {
                        "宏观研报": "https://data.eastmoney.com/report/zw_macresearch.jshtml?encodeUrl=",
                        "策略研报": "https://data.eastmoney.com/report/zw_strategy.jshtml?encodeUrl=",
                        "晨报": "https://data.eastmoney.com/report/zw_morning.jshtml?encodeUrl=",
                    }.get(category, "")
                    report_url = (pref + str(raw.get("encodeUrl") or ""))[:1024] if pref else ""
                if not report_url and raw.get("infoCode"):
                    report_url = f"https://data.eastmoney.com/report/zw_industry.jshtml?infocode={raw.get('infoCode')}"[:1024]
                
                entries.append(YanbaoEntry(
                    category=category,
                    title=title,
                    org_name=org,
                    pub_date=norm_date(pub),
                    stock_code=code,
                    report_url=report_url,
                    raw=raw
                ))
            return self._repo.insert_yanbao_batch(category, [e.model_dump() for e in entries], batch)

        total = 0
        errors: list[str] = []

        def _fetch_get(url: str, params: dict[str, Any]) -> GenericResponseDTO:
            try:
                resp = sess.get(url, params=params, timeout=20)
                return parser.parse_json_or_jsonp(resp.text)
            except Exception as exc:  # noqa: BLE001
                return {"_error": f"{type(exc).__name__}:{exc}"}

        def _fetch_post(url: str, body: dict[str, Any]) -> GenericResponseDTO:
            try:
                resp = sess.post(url, json=body, timeout=20)
                return parser.parse_json_or_jsonp(resp.text)
            except Exception as exc:  # noqa: BLE001
                return {"_error": f"{type(exc).__name__}:{exc}"}

        for t in types:
            if t == "industry":
                base = "https://reportapi.eastmoney.com/report/list"
                cat = "行业研报"
                qtype = "1"
                for p in range(1, page_cap + 1):
                    params = {"pageSize": cap, "pageNo": p, "beginTime": begin, "endTime": end, "qType": qtype, "industry": "*", "industryCode": "*", "rating": "*", "ratingChange": "*", "fields": "", "orgCode": "", "rcode": ""}
                    data = _fetch_get(base, params)
                    if data.get("_error"):
                        errors.append(f"{cat}:{data['_error']}")
                        break
                    items = (data.get("data") or []) if isinstance(data, dict) else []
                    if not items: break
                    total += _emit_items(cat, items)
                    if str(items[-1].get("publishDate") or "")[:10] < begin: break
                    time.sleep(delay)
            elif t == "stock":
                base = "https://reportapi.eastmoney.com/report/list2"
                cat = "个股研报"
                for p in range(1, page_cap + 1):
                    body = {"pageSize": cap, "pageNo": p, "beginTime": begin, "endTime": end, "code": "*", "industryCode": "*", "rating": None, "ratingChange": None, "orgCode": None, "rcode": ""}
                    data = _fetch_post(base, body)
                    if data.get("_error"):
                        errors.append(f"{cat}:{data['_error']}")
                        break
                    items = (data.get("data") or []) if isinstance(data, dict) else []
                    if not items: break
                    total += _emit_items(cat, items)
                    if str(items[-1].get("publishDate") or "")[:10] < begin: break
                    time.sleep(delay)
            elif t in ("macro", "strategy", "morning"):
                base = "https://reportapi.eastmoney.com/report/jg"
                cat = {"macro": "宏观研报", "strategy": "策略研报", "morning": "晨报"}[t]
                qtype = {"macro": "3", "strategy": "2", "morning": "4"}[t]
                for p in range(1, page_cap + 1):
                    params = {"pageSize": cap, "pageNo": p, "beginTime": begin, "endTime": end, "qType": qtype, "industry": "*", "industryCode": "*", "rating": "*", "ratingChange": "*", "fields": "", "orgCode": "", "rcode": ""}
                    data = _fetch_get(base, params)
                    if data.get("_error"):
                        errors.append(f"{cat}:{data['_error']}")
                        break
                    items = (data.get("data") or []) if isinstance(data, dict) else []
                    if not items: break
                    total += _emit_items(cat, items)
                    if str(items[-1].get("publishDate") or "")[:10] < begin: break
                    time.sleep(delay)

        self._repo.set_meta("last_yanbao_ingest", json.dumps({"at": datetime.now().isoformat(), "rows": total, "source": "eastmoney_api"}, ensure_ascii=False))
        return {"ok": True, "rows": total, "source": "eastmoney_api", "begin": begin, "end": end, "errors": errors}

    def ingest_yanbao_akshare_universe(
        self,
        *,
        symbols: list[str],
        per_symbol_limit: int = 10,
        sleep_sec: float = 0.15,
    ) -> GenericResponseDTO:
        """用 AkShare 单股研报接口聚合入库。"""
        from app.modules.system.services.helpers.cn_fundamentals_access import get_cn_fundamentals_port
        from app.domain.shared.symbol_normalizer import SymbolNormalizer
        prov = get_cn_fundamentals_port()
        cap = max(1, min(int(per_symbol_limit), 60))
        delay = max(0.05, min(float(sleep_sec), 2.0))
        batch = datetime.now().strftime("%Y%m%d_%H%M%S")
        total = 0
        parser = EastmoneyParser()
        
        for sym in symbols:
            code = SymbolNormalizer.normalize_code(sym)
            if len(code) != 6: continue
            rows, err = prov.fetch_research_reports(code, limit=cap)
            if err:
                time.sleep(delay)
                continue
            
            entries: list[YanbaoEntry] = []
            for rec in rows or []:
                rr = {str(k): json_safe(v) for k, v in (rec or {}).items()}
                title = parser.pick_first_str(rr, key_needles=("标题", "报告", "研报", "name", "title"), value_regex=None)[:512]
                if not title: continue
                org = parser.pick_first_str(rr, key_needles=("机构", "org", "ORG", "券商"), value_regex=None)[:128]
                pub = parser.pick_first_str(rr, key_needles=("日期", "时间", "date", "pub"), value_regex=r"\b\d{4}-\d{2}-\d{2}\b")
                link = parser.pick_first_str(rr, key_needles=("链接", "url", "URL", "href"), value_regex=r"https?://")[:1024]
                
                entries.append(YanbaoEntry(
                    category="个股研报",
                    title=title,
                    org_name=org,
                    pub_date=norm_date(pub),
                    stock_code=code,
                    report_url=link,
                    raw=rr
                ))
            n = self._repo.insert_yanbao_batch("个股研报", [e.model_dump() for e in entries], batch)
            total += n
            time.sleep(delay)
            
        self._repo.set_meta("last_yanbao_ingest", json.dumps({"at": datetime.now().isoformat(), "rows": total, "source": "akshare_universe"}))
        return {"ok": True, "rows": total, "source": "akshare_universe"}

    def longhu_for_stock(self, code: str, *, limit: int = 20) -> list[dict[str, Any]]:
        return self._repo.list_longhu_for_code(code, limit=limit)

    def longhu_day(
        self,
        trade_date: str | None,
        *,
        limit: int = 400,
        offset: int = 0,
    ) -> tuple[str | None, list[dict[str, Any]]]:
        td = (trade_date or "").strip()[:10] or self._repo.latest_longhu_trade_date()
        if not td:
            return None, []
        return td, self._repo.list_longhu_by_date(td, limit=limit, offset=offset)

    def count_longhu_day(self, trade_date: str | None) -> int:
        td = (trade_date or "").strip()[:10] or self._repo.latest_longhu_trade_date()
        if not td:
            return 0
        return self._repo.count_longhu_by_date(td)

    def yanbao_list(self, **kwargs: Any) -> list[dict[str, Any]]:
        return self._repo.list_yanbao(**kwargs)

    def backfill_stock_history_from_tdx(self, limit: int | None = None) -> GenericResponseDTO:
        """[TDX专用] 全量历史入库（兼容旧入口）。"""
        if self._tdx_root is None: return {"ok": False, "error": "tdx_root_not_set"}
        from app.infrastructure.repositories.deps import create_tdx_dayk_sync_service

        return create_tdx_dayk_sync_service(base_dir=BASE_DIR).full_sync_from_tdx_dayk(limit=limit)

    def tdx_local_status(self) -> GenericResponseDTO:
        """本机通达信根目录是否可用及关键子路径。"""
        if self._tdx_root is None:
            return {"configured": False, "root": "", "vipdoc_sh_lday": False, "hq_cache": False, "gbbq": False}
        paths = TdxLocalPaths(self._tdx_root) # type: ignore
        return {"configured": True, "root": str(self._tdx_root), "vipdoc_sh_lday": (paths.root / "vipdoc" / "sh" / "lday").is_dir(), "hq_cache": paths.hq_cache.is_dir(), "gbbq": paths.gbbq_file.is_file()}

    def get_tdx_local_cn_snapshot(self, symbol: str, *, lday_tail: int = 40, gbbq_tail: int = 12, max_blocks: int = 24) -> GenericResponseDTO:
        """单只 A 股：本地 lday 尾部、板块归属、gbbq 股本变迁摘要。"""
        from app.domain.shared.symbol_normalizer import SymbolNormalizer
        code = SymbolNormalizer.normalize_code(symbol)
        if len(code) != 6 or not code.isdigit(): return {"ok": False, "error": "invalid_cn_code", "code": code}
        st = self.tdx_local_status()
        if not st.get("configured"): return {"ok": False, "error": "tdx_root_not_configured", "status": st, "code": code}
        paths = TdxLocalPaths(self._tdx_root)
        lday_path = paths.lday_file(market_sh=(SymbolNormalizer.market_id(code) == 1), code6=code)
        tdx_port = get_tdx_local_file_port()
        lday_rows = tdx_port.read_lday_file(lday_path, tail=max(1, min(lday_tail, 2000)))
        blocks, _ = tdx_port.list_blocks_for_code(paths.hq_cache, code, max_block_names=max(1, min(max_blocks, 80)))
        gbbq, _ = tdx_port.gbbq_rows_for_code(paths.gbbq_file, code, tail=max(1, min(gbbq_tail, 80)))
        return {"ok": True, "code": code, "lday_tail": lday_rows, "block_names": blocks, "gbbq_tail": gbbq, "status": st}
