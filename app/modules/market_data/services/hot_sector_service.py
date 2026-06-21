from __future__ import annotations
"""热点板块服务：东财 / 同花顺 / 开盘啦 / 选股通 概念与行业板块。"""


import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Any, Callable, Literal

import requests
from requests import exceptions as req_exc

from app.modules.system.services.helpers.cn_sector_board_access import get_cn_sector_board_port
from app.core.logger import get_logger
from app.core.runtime_config import get_runtime_int
from app.domain.shared.sector_board_metrics import rise_ratio
from app.infrastructure.providers import DEFAULT_UA

logger = get_logger(__name__)

SectorKind = Literal["concept", "industry", "region", "csrc"]
DataVendor = Literal["em", "ths", "kpl", "xgt", "akshare", "all"]

_CLIST_URL = "https://push2.eastmoney.com/api/qt/clist/get"
_HEADERS = {
    "User-Agent": DEFAULT_UA,
    "Referer": "https://quote.eastmoney.com/center/gridlist.html",
    "Accept": "application/json, text/plain, */*",
}
_UT = "bd1d3dd2d51b84811cb1e0f1c50b3a94"


class HotSectorService:
    """拉取并缓存热点板块涨跌幅（参考东财 clist 板块列表）。"""

    def __init__(self, *, cache_ttl_sec: int = 300) -> None:
        self._cache: dict[str, Any] = {}
        self._cache_time: dict[str, float] = {}
        self._cache_ttl = cache_ttl_sec
        self._ths_session = None
        self._sector_port = None
        self._init_ths_session()

    def _port(self):
        if self._sector_port is None:
            self._sector_port = get_cn_sector_board_port()
        return self._sector_port

    def _init_ths_session(self) -> None:
        """初始化同花顺登录会话（凭证来自 ``THS_USERNAME`` / ``THS_PASSWORD``）。"""
        self._ths_session = self._port().get_ths_session_from_settings()
        if self._ths_session is not None:
            logger.debug("THS session initialized via sector board port")

    def _cache_get(self, key: str) -> Any | None:
        ts = self._cache_time.get(key)
        if ts is None or (time.time() - ts) >= self._cache_ttl:
            return None
        return self._cache.get(key)

    def _cache_set(self, key: str, value: object) -> None:
        self._cache[key] = value
        self._cache_time[key] = time.time()

    def _fetch_clist(self, *, fs: str, page_size: int = 80) -> list[dict[str, Any]]:
        params = {
            "pn": 1,
            "pz": page_size,
            "po": 1,
            "np": 1,
            "ut": _UT,
            "fltt": 2,
            "invt": 2,
            "fid": "f3",
            "fs": fs,
            "fields": "f12,f14,f2,f3,f4,f5,f6,f20,f104,f105,f128,f136,f140",
            "_": int(datetime.now().timestamp() * 1000),
        }
        last_exc: Exception | None = None
        for attempt in range(2):
            session = requests.Session()
            session.headers.update(_HEADERS)
            try:
                resp = session.get(_CLIST_URL, params=params, timeout=12)
                resp.raise_for_status()
                payload = resp.json()
                return self._parse_clist_diff(payload)
            except (req_exc.RequestException, ValueError) as exc:
                last_exc = exc
                if attempt == 0:
                    logger.warning("eastmoney clist retry fs=%s: %s", fs, exc)
                    time.sleep(1.5)
                    continue
        logger.warning("eastmoney clist failed fs=%s: %s", fs, last_exc)
        return []

    @staticmethod
    def _parse_clist_diff(payload: dict[str, Any]) -> list[dict[str, Any]]:
        diff = (payload.get("data") or {}).get("diff") or []
        rows: list[dict[str, Any]] = []
        for item in diff:
            code = str(item.get("f12") or "").strip()
            name = str(item.get("f14") or "").strip()
            if not code or not name:
                continue
            change_pct = _to_float(item.get("f3"))
            up_cnt = int(_to_float(item.get("f104")))
            down_cnt = int(_to_float(item.get("f105")))
            leader_name = str(item.get("f128") or item.get("f140") or "").strip() or None
            leader_pct = _to_float(item.get("f136"))
            if leader_pct == 0.0 and item.get("f141") is not None:
                leader_pct = _to_float(item.get("f141"))
            rows.append(
                {
                    "sector_code": code,
                    "name": name,
                    "change_pct": change_pct,
                    "price": _to_float(item.get("f2")),
                    "amount": _to_float(item.get("f6")),
                    "volume": _to_float(item.get("f5")),
                    "turnover_rate": _to_float(item.get("f20")),
                    "rise_ratio": rise_ratio(up_cnt, down_cnt),
                    "rise_count": up_cnt,
                    "fall_count": down_cnt,
                    "leader_name": leader_name,
                    "leader_change_pct": leader_pct if leader_name else None,
                }
            )
        return rows

    def get_em_concepts(self, *, limit: int = 80) -> list[dict[str, Any]]:
        key = f"em_concepts_{limit}"
        cached = self._cache_get(key)
        if cached is not None:
            return cached

        rows = self._fetch_clist(fs="m:90+t:2", page_size=limit)
        for row in rows:
            row["source"] = "东方财富概念"
            row["kind"] = "concept"
            row["provider"] = "em"
        self._cache_set(key, rows)
        return rows

    def get_em_industries(self, *, limit: int = 80) -> list[dict[str, Any]]:
        key = f"em_industries_{limit}"
        cached = self._cache_get(key)
        if cached is not None:
            return cached

        rows = self._fetch_clist(fs="m:90+t:1", page_size=limit)
        for row in rows:
            row["source"] = "东方财富行业"
            row["kind"] = "industry"
            row["provider"] = "em"
        self._cache_set(key, rows)
        return rows

    def get_ths_concepts(self, *, limit: int = 80) -> list[dict[str, Any]]:
        key = f"ths_concepts_{limit}"
        cached = self._cache_get(key)
        if cached is not None:
            return cached
        rows = self._port().fetch_ths_concept_boards(limit=limit, session=self._ths_session)
        self._cache_set(key, rows)
        return rows

    def get_kpl_concepts(self, *, limit: int = 80) -> list[dict[str, Any]]:
        key = f"kpl_concepts_{limit}"
        cached = self._cache_get(key)
        if cached is not None:
            return cached
        rows = self._port().fetch_kpl_boards(kind="concept", limit=limit)
        self._cache_set(key, rows)
        return rows

    def get_kpl_regions(self, *, limit: int = 80) -> list[dict[str, Any]]:
        key = f"kpl_regions_{limit}"
        cached = self._cache_get(key)
        if cached is not None:
            return cached
        rows = self._port().fetch_kpl_boards(kind="region", limit=limit)
        self._cache_set(key, rows)
        return rows

    def get_kpl_industries(self, *, limit: int = 80) -> list[dict[str, Any]]:
        key = f"kpl_industries_{limit}"
        cached = self._cache_get(key)
        if cached is not None:
            return cached
        rows = self._port().fetch_kpl_boards(kind="industry", limit=limit)
        self._cache_set(key, rows)
        return rows

    def get_xgt_concepts(self, *, limit: int = 80) -> list[dict[str, Any]]:
        key = f"xgt_concepts_{limit}"
        cached = self._cache_get(key)
        if cached is not None:
            return cached
        rows = self._port().fetch_xgt_concept_boards(limit=limit)
        self._cache_set(key, rows)
        return rows

    def _get_akshare_concepts(self, limit: int = 50) -> list[dict[str, Any]]:
        """akshare概念板块"""
        key = f"akshare_concepts_{limit}"
        cached = self._cache_get(key)
        if cached is not None:
            return cached
        try:
            import akshare as ak
            df = ak.stock_board_concept_name_ths()
            rows = []
            for _, r in df.head(limit).iterrows():
                name = str(r.get("板块名称", "")).strip()
                change = r.get("涨跌幅")
                if name and change is not None:
                    rows.append({
                        "provider": "akshare",
                        "sector_code": f"AKSHARE_CONCEPT_{name}",
                        "name": name,
                        "change_pct": float(change),
                        "source": "akshare概念",
                    })
            self._cache_set(key, rows)
            return rows
        except ImportError:
            logger.warning("akshare not installed")
        except Exception as e:
            logger.warning("akshare concept fetch failed: %s", e)
        return []

    def _get_akshare_industries(self, limit: int = 50) -> list[dict[str, Any]]:
        """akshare行业板块"""
        key = f"akshare_industries_{limit}"
        cached = self._cache_get(key)
        if cached is not None:
            return cached
        try:
            import akshare as ak
            df = ak.stock_board_industry_name_ths()
            rows = []
            for _, r in df.head(limit).iterrows():
                name = str(r.get("板块名称", "")).strip()
                change = r.get("涨跌幅")
                if name and change is not None:
                    rows.append({
                        "provider": "akshare",
                        "sector_code": f"AKSHARE_INDUSTRY_{name}",
                        "name": name,
                        "change_pct": float(change),
                        "source": "akshare行业",
                    })
            self._cache_set(key, rows)
            return rows
        except ImportError:
            logger.warning("akshare not installed")
        except Exception as e:
            logger.warning("akshare industry fetch failed: %s", e)
        return []

    def get_ths_industries(self, *, limit: int = 80) -> list[dict[str, Any]]:
        key = f"ths_industries_{limit}"
        cached = self._cache_get(key)
        if cached is not None:
            return cached
        rows = self._port().fetch_ths_industry_boards(limit=limit, session=self._ths_session)
        self._cache_set(key, rows)
        return rows

    def get_ths_regions(self, *, limit: int = 80) -> list[dict[str, Any]]:
        key = f"ths_regions_{limit}"
        cached = self._cache_get(key)
        if cached is not None:
            return cached
        rows = self._port().fetch_ths_region_boards(limit=limit, session=self._ths_session)
        self._cache_set(key, rows)
        return rows

    def get_ths_csrc_industries(self, *, limit: int = 80) -> list[dict[str, Any]]:
        key = f"ths_csrc_{limit}"
        cached = self._cache_get(key)
        if cached is not None:
            return cached
        rows = self._port().fetch_ths_csrc_boards(limit=limit, session=self._ths_session)
        self._cache_set(key, rows)
        return rows

    def get_ths_all_boards(self, *, limit_per_kind: int = 60) -> list[dict[str, Any]]:
        key = f"ths_all_{limit_per_kind}"
        cached = self._cache_get(key)
        if cached is not None:
            return cached
        rows = self._port().fetch_ths_all_boards(limit_per_kind=limit_per_kind, session=self._ths_session)
        self._cache_set(key, rows)
        return rows

    def _run_fetch_tasks(
        self,
        tasks: list[tuple[str, Callable[[], list[dict[str, Any]]]]],
        *,
        budget_sec: float,
    ) -> tuple[list[dict[str, Any]], list[str]]:
        """并行拉取多源榜单，超时后返回已完成部分。"""
        if not tasks:
            return [], []
        rows: list[dict[str, Any]] = []
        warnings: list[str] = []
        with ThreadPoolExecutor(max_workers=min(6, len(tasks))) as pool:
            futures = {pool.submit(fn): label for label, fn in tasks}
            try:
                for fut in as_completed(futures, timeout=max(3.0, budget_sec)):
                    label = futures[fut]
                    try:
                        rows.extend(fut.result())
                    except Exception as exc:
                        logger.warning("hot sector fetch %s failed: %s", label, exc)
                        warnings.append(f"{label}: {exc}")
            except TimeoutError:
                for fut, label in futures.items():
                    if not fut.done():
                        fut.cancel()
                        warnings.append(f"{label}: timeout")
        return rows, warnings

    def get_hot_sectors(
        self,
        limit: int = 50,
        *,
        vendor: DataVendor = "all",
        budget_sec: float | None = None,
    ) -> list[dict[str, Any]]:
        """按涨跌幅合并概念+行业；``vendor`` 可选东财/同花顺/akshare/全部。"""
        v = (vendor or "all").strip().lower()
        per = max(20, min(limit, 60))
        budget = budget_sec if budget_sec is not None else float(
            get_runtime_int("HOT_SECTOR_LIVE_BUDGET_SEC", 22)
        )

        tasks: list[tuple[str, Callable[[], list[dict[str, Any]]]]] = []
        if v in ("all", "em"):
            tasks.append(("em_concepts", lambda: self.get_em_concepts(limit=limit)))
            tasks.append(("em_industries", lambda: self.get_em_industries(limit=limit)))
        if v in ("all", "ths"):
            tasks.append(("ths_all", lambda: self.get_ths_all_boards(limit_per_kind=per)))
        if v in ("all", "kpl"):
            tasks.append(("kpl", lambda: (
                self.get_kpl_concepts(limit=limit)
                + self.get_kpl_regions(limit=limit)
                + self.get_kpl_industries(limit=limit)
            )))
        if v in ("all", "xgt"):
            tasks.append(("xgt", lambda: self.get_xgt_concepts(limit=limit)))
        if v == "akshare":
            tasks.append(("akshare", lambda: (
                self._get_akshare_concepts(limit=limit)
                + self._get_akshare_industries(limit=limit)
            )))

        rows, _warnings = self._run_fetch_tasks(tasks, budget_sec=budget)

        merged: dict[str, dict[str, Any]] = {}
        for row in rows:
            key = f"{row.get('provider', 'em')}:{row.get('sector_code', row.get('name', ''))}"
            prev = merged.get(key)
            if prev is None or row["change_pct"] > prev["change_pct"]:
                merged[key] = row

        sectors = sorted(merged.values(), key=lambda x: x["change_pct"], reverse=True)
        return sectors[:limit]

    def get_sector_members(
        self,
        sector_code: str,
        *,
        limit: int = 80,
        kind: SectorKind = "concept",
        sector_name: str | None = None,
        provider: str | None = None,
    ) -> list[dict[str, Any]]:
        """板块成分股：按 provider 或代码规则分流。"""
        code = (sector_code or "").strip().upper()
        prov = (provider or "").strip().lower()
        if not code:
            return []

        if prov == "kpl" or (not prov and self._port().is_kpl_sector_code(code)):
            key = f"kpl_members_{code}_{limit}"
            cached = self._cache_get(key)
            if cached is not None:
                return cached
            rows = self._port().fetch_kpl_board_members(code, limit=limit)
            self._cache_set(key, rows)
            return rows

        if prov == "xgt" or (not prov and self._port().is_xgt_plate_code(code)):
            key = f"xgt_members_{code}_{limit}"
            cached = self._cache_get(key)
            if cached is not None:
                return cached
            rows = self._port().fetch_xgt_board_members(code, limit=limit)
            self._cache_set(key, rows)
            return rows

        if prov == "ths" or (not prov and self._port().is_ths_sector_code(code)):
            ths_kind = self._port().normalize_ths_board_kind(kind)
            key = f"ths_members_{ths_kind}_{code}_{limit}"
            cached = self._cache_get(key)
            if cached is not None:
                return cached
            rows = self._port().fetch_ths_board_members(
                code,
                kind=ths_kind,
                sector_name=sector_name,
                limit=limit,
                session=self._ths_session,
            )
            self._cache_set(key, rows)
            return rows

        key = f"members_{code}_{limit}"
        cached = self._cache_get(key)
        if cached is not None:
            return cached

        rows = self._fetch_clist(fs=f"b:{code}", page_size=limit)
        members: list[dict[str, Any]] = []
        for row in rows:
            sym6 = "".join(ch for ch in row["sector_code"] if ch.isdigit())[-6:].zfill(6)
            market = "sh" if sym6.startswith(("5", "6", "9")) else "sz"
            if sym6.startswith(("4", "8")):
                market = "bj"
            members.append(
                {
                    "symbol": f"{market}{sym6}",
                    "code": sym6,
                    "name": row["name"],
                    "change_pct": row["change_pct"],
                    "price": row["price"],
                    "amount": row["amount"],
                    "volume": row["volume"],
                }
            )
        members.sort(key=lambda x: x["change_pct"], reverse=True)
        self._cache_set(key, members)
        return members


def _to_float(value: str | float | int | None) -> float:
    try:
        if value is None or value == "-":
            return 0.0
        return float(value)
    except (TypeError, ValueError):
        return 0.0


_hot_sector_service: HotSectorService | None = None


def get_hot_sector_service() -> HotSectorService:
    global _hot_sector_service
    if _hot_sector_service is None:
        _hot_sector_service = HotSectorService()
    return _hot_sector_service
