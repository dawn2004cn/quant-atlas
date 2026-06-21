from __future__ import annotations
"""同花顺板块与成分股（概念/地域/行业/证监会行业，q.10jqka.com.cn）。"""


import re
import time
from typing import Any, Literal

import requests
from requests import exceptions as req_exc

from app.core.logger import get_logger
from app.infrastructure.providers import DEFAULT_UA

logger = get_logger(__name__)

ThsBoardKind = Literal["concept", "industry", "region", "csrc"]

_KIND_META: dict[ThsBoardKind, dict[str, str]] = {
    "concept": {"path": "gn", "label": "同花顺概念", "sector_kind": "concept"},
    "region": {"path": "dy", "label": "同花顺地域", "sector_kind": "region"},
    "industry": {"path": "thshy", "label": "同花顺行业", "sector_kind": "industry"},
    "csrc": {"path": "zjhhy", "label": "同花顺证监会行业", "sector_kind": "csrc"},
}

_THS_HEADERS = {
    "User-Agent": DEFAULT_UA,
    "Referer": "http://q.10jqka.com.cn/",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9",
    "X-Requested-With": "XMLHttpRequest",
}

_CODE_RE = re.compile(r"/detail/code/([^/]+)/", re.I)
_PCT_RE = re.compile(r"([+-]?\d+\.?\d*)")

_THS_LOGIN_URL = "https://upass.10jqka.com.cn/login"
_THS_LOGIN_POST_URL = "https://upass.10jqka.com.cn/login"

_session_cache: dict[str, requests.Session] = {}


def _index_ajax_url(kind: ThsBoardKind, page: int) -> str:
    """板块列表分页 AJAX（须用 index 路径；detail 无 code 时仅部分类型可解析）。"""
    path = _KIND_META[kind]["path"]
    return (
        f"http://q.10jqka.com.cn/{path}/index/field/additional/"
        f"order/desc/page/{page}/ajax/1/"
    )


def _index_ajax_url_detail_fallback(kind: ThsBoardKind, page: int) -> str:
    """部分环境 index 无表格时回退到 detail 列表接口。"""
    path = _KIND_META[kind]["path"]
    return (
        f"http://q.10jqka.com.cn/{path}/detail/field/199112/"
        f"order/desc/page/{page}/ajax/1/"
    )


def _index_page_url(kind: ThsBoardKind) -> str:
    path = _KIND_META[kind]["path"]
    return f"http://q.10jqka.com.cn/{path}/"


def _members_ajax_url(kind: ThsBoardKind, code: str, page: int) -> str:
    path = _KIND_META[kind]["path"]
    safe_code = requests.utils.quote(str(code).strip(), safe="")
    return (
        f"http://q.10jqka.com.cn/{path}/detail/field/199112/"
        f"order/desc/page/{page}/ajax/1/code/{safe_code}"
    )


def _new_session(*, referer_path: str) -> requests.Session:
    session = requests.Session()
    session.headers.update(_THS_HEADERS)
    try:
        warm = session.get(_index_page_url_by_path(referer_path), timeout=12)
        warm.raise_for_status()
        # 尝试 GBK 解码
        try:
            warm.encoding = "gbk"
            _ = warm.text  # 触发改解码
        except Exception as e:
            logger.warning("cn_ths_sectors.py._new_session: %s", e)
    except req_exc.RequestException as exc:
        logger.debug("THS session warmup path=%s: %s", referer_path, exc)
    return session


def ths_login(username: str, password: str) -> requests.Session | None:
    """登录同花顺账号，返回已认证的 Session。"""
    session = requests.Session()
    session.headers.update(_THS_HEADERS)

    try:
        session.get(_THS_LOGIN_URL, timeout=10)
        resp = session.post(
            _THS_LOGIN_POST_URL,
            data={
                "username": username,
                "password": password,
                "remember": "1",
            },
            timeout=15,
            allow_redirects=True,
        )
        check = session.get("https://www.10jqka.com.cn/", timeout=10)
        if "username" in check.text.lower() or username in check.text:
            logger.info("THS login successful for user=%s", username)
            _session_cache[username] = session
            return session

        logger.warning(
            "THS login failed for user=%s status=%s",
            username,
            resp.status_code,
        )
    except req_exc.RequestException as exc:
        logger.warning("THS login request failed for user=%s: %s", username, exc)
    except Exception as exc:
        logger.warning("THS login error for user=%s", username, exc_info=True)

    return None


def get_ths_session(username: str | None = None, password: str | None = None) -> requests.Session:
    """获取已登录的 THS Session，未登录则返回新 Session。"""
    if username and username in _session_cache:
        return _session_cache[username]

    if username and password:
        session = ths_login(username, password)
        if session:
            return session

    return _new_session(referer_path="gn")


def get_ths_session_from_settings() -> requests.Session:
    """从 ``get_settings().ths`` 读取凭证；未配置时返回匿名 Session。"""
    try:
        from app.config import get_settings

        ths = get_settings().ths
        if ths.has_credentials:
            return get_ths_session(ths.username, ths.password)
    except Exception as exc:
        logger.debug("THS settings unavailable, using anonymous session: %s", exc)
    return _new_session(referer_path="gn")


def _index_page_url_by_path(path: str) -> str:
    return f"http://q.10jqka.com.cn/{path}/"


def _get_html(session: requests.Session, url: str, *, timeout: float = 12.0) -> str:
    resp = session.get(url, timeout=timeout)
    resp.raise_for_status()
    # THS 网站使用 GBK 编码，直接解码 content
    try:
        return resp.content.decode("gbk")
    except (UnicodeDecodeError, LookupError):
        resp.encoding = "gbk"
        return resp.text


def _parse_pct(text: str) -> float:
    raw = (text or "").strip().replace("%", "").replace("％", "")
    m = _PCT_RE.search(raw)
    if not m:
        return 0.0
    try:
        return float(m.group(1))
    except ValueError:
        return 0.0


def _parse_board_index_html(
    html: str,
    *,
    ths_kind: ThsBoardKind,
    source_label: str,
) -> list[dict[str, Any]]:
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        logger.warning("BeautifulSoup not installed; THS board scrape skipped")
        return []

    sector_kind = _KIND_META[ths_kind]["sector_kind"]
    soup = BeautifulSoup(html, "html.parser")
    table = soup.select_one("table.m-table") or soup.find("table")
    if not table:
        return _parse_board_links_fallback(soup, ths_kind=ths_kind, source_label=source_label)

    pct_col: int | None = None
    for tr in table.select("tr")[:4]:
        headers = tr.select("th")
        if not headers:
            continue
        for idx, th in enumerate(headers):
            if "涨跌幅" in th.get_text(strip=True):
                pct_col = idx
                break
        if pct_col is not None:
            break

    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for tr in table.select("tr"):
        link = tr.select_one('a[href*="/detail/code/"]')
        if not link:
            continue
        href = link.get("href") or ""
        m = _CODE_RE.search(href)
        if not m:
            continue
        code = m.group(1).strip().upper()
        if not code or code in seen:
            continue
        seen.add(code)
        name = link.get_text(strip=True)
        if not name:
            continue
        tds = tr.select("td")
        change_pct = 0.0
        if pct_col is not None and pct_col < len(tds):
            change_pct = _parse_pct(tds[pct_col].get_text(strip=True))
        else:
            for td in tds:
                cls = " ".join(td.get("class") or [])
                txt = td.get_text(strip=True)
                if "%" in txt or "c-rise" in cls or "c-fall" in cls:
                    change_pct = _parse_pct(txt)
                    break
                if txt and re.fullmatch(r"[+-]?\d+\.?\d*", txt):
                    val = _parse_pct(txt)
                    if abs(val) <= 30:
                        change_pct = val
                        break
        rows.append(
            {
                "sector_code": code,
                "name": name,
                "change_pct": change_pct,
                "price": 0.0,
                "amount": 0.0,
                "volume": 0.0,
                "turnover_rate": 0.0,
                "source": source_label,
                "kind": sector_kind,
                "provider": "ths",
                "ths_board_kind": ths_kind,
            }
        )
    return rows


def _parse_board_links_fallback(
    soup: Any,
    *,
    ths_kind: ThsBoardKind,
    source_label: str,
) -> list[dict[str, Any]]:
    """从页面中所有板块详情链接提取榜单（兼容 index/ajax 非表格结构）。"""
    sector_kind = _KIND_META[ths_kind]["sector_kind"]
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for link in soup.select('a[href*="/detail/code/"]'):
        href = link.get("href") or ""
        m = _CODE_RE.search(href)
        if not m:
            continue
        code = m.group(1).strip().upper()
        if not code or code in seen:
            continue
        seen.add(code)
        name = link.get_text(strip=True)
        if not name:
            continue
        change_pct = 0.0
        parent = link.find_parent("tr") or link.find_parent("li") or link.parent
        if parent is not None:
            for td in getattr(parent, "select", lambda _s: [])("td"):
                txt = td.get_text(strip=True)
                if "%" in txt or "c-rise" in " ".join(td.get("class") or []):
                    change_pct = _parse_pct(txt)
                    break
        rows.append(
            {
                "sector_code": code,
                "name": name,
                "change_pct": change_pct,
                "price": 0.0,
                "amount": 0.0,
                "volume": 0.0,
                "turnover_rate": 0.0,
                "source": source_label,
                "kind": sector_kind,
                "provider": "ths",
                "ths_board_kind": ths_kind,
            }
        )
    return rows


def _parse_members_html(html: str) -> list[dict[str, Any]]:
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        return []

    soup = BeautifulSoup(html, "html.parser")
    table = soup.select_one("table.m-table") or soup.find("table")
    if not table:
        return []

    members: list[dict[str, Any]] = []
    for tr in table.select("tr"):
        tds = tr.select("td")
        if len(tds) < 2:
            continue
        code_a = tr.select_one('a[href*="stockpage.10jqka.com.cn"]') or tr.select_one("a")
        if not code_a:
            continue
        name = ""
        sym6 = ""
        href = code_a.get("href") or ""
        m = re.search(r"/(\d{6})/", href)
        if m:
            sym6 = m.group(1)
        else:
            sym6 = "".join(ch for ch in code_a.get_text(strip=True) if ch.isdigit())[-6:].zfill(6)
        if len(tds) >= 2:
            name = tds[1].get_text(strip=True) or code_a.get_text(strip=True)
        change_pct = 0.0
        price = 0.0
        for td in tds[2:]:
            txt = td.get_text(strip=True)
            if "%" in txt:
                change_pct = _parse_pct(txt)
            elif txt.replace(".", "").replace("-", "").isdigit() and price == 0.0:
                try:
                    price = float(txt)
                except ValueError as e:
                    logger.warning("cn_ths_sectors.py._parse_members_html: %s", e)
        if not sym6 or len(sym6) != 6:
            continue
        market = "bj" if sym6.startswith(("4", "8")) else ("sh" if sym6.startswith(("5", "6", "9")) else "sz")
        members.append(
            {
                "symbol": f"{market}{sym6}",
                "code": sym6,
                "name": name,
                "change_pct": change_pct,
                "price": price,
                "amount": 0.0,
                "volume": 0.0,
            }
        )
    return members


def _fetch_board_index_akshare(ths_kind: ThsBoardKind, *, limit: int, source_label: str) -> list[dict[str, Any]]:
    """使用 akshare 获取同花顺板块列表（fallback）。"""
    try:
        import akshare as ak
    except ImportError:
        return []
    
    try:
        if ths_kind == "concept":
            df = ak.stock_board_concept_name_ths()
        elif ths_kind == "industry":
            df = ak.stock_board_industry_name_ths()
        else:
            # region 和 csrc 没有 akshare 接口
            return []
        
        if df is None or df.empty:
            return []
        
        # 修复编码问题
        for col in df.columns:
            if df[col].dtype == object:
                df[col] = df[col].apply(lambda x: _fix_encoding(x) if isinstance(x, str) else x)
        
        sector_kind = _KIND_META[ths_kind]["sector_kind"]
        rows = []
        for _, row in df.head(limit).iterrows():
            code = str(row.get("板块代码") or row.get("code") or "").strip()
            name = str(row.get("板块名称") or row.get("name") or "").strip()
            if not code or not name:
                continue
            rows.append({
                "sector_code": code,
                "name": name,
                "change_pct": float(row.get("涨跌幅") or row.get("change_pct") or 0),
                "price": 0.0,
                "amount": float(row.get("成交额") or row.get("amount") or 0),
                "volume": float(row.get("成交量") or row.get("volume") or 0),
                "turnover_rate": float(row.get("换手率") or row.get("turnover") or 0),
                "source": source_label,
                "kind": sector_kind,
                "provider": "ths",
                "ths_board_kind": ths_kind,
            })

        logger.info("akshare THS %s got %s boards", ths_kind, len(rows))
        return rows
    except Exception as exc:
        logger.warning("akshare THS %s failed: %s", ths_kind, exc)
        return []


def _fix_encoding(text: str) -> str:
    """尝试修复编码问题。"""
    try:
        # 尝试 latin1 -> gbk 转换
        return text.encode("latin1").decode("gbk")
    except (UnicodeEncodeError, UnicodeDecodeError):
        try:
            # 尝试 utf-8 -> gbk 转换
            return text.encode("utf-8").decode("gbk")
        except (UnicodeEncodeError, UnicodeDecodeError):
            return text


def _scrape_board_pages(
    ths_kind: ThsBoardKind,
    *,
    limit: int,
    session: requests.Session,
    label: str,
) -> list[dict[str, Any]]:
    """抓取榜单：index/ajax → detail/ajax 回退 → 静态首页。"""
    out: list[dict[str, Any]] = []
    max_pages = 4 if ths_kind in ("region", "csrc") else 6

    def _collect_from_url(url: str) -> list[dict[str, Any]]:
        try:
            html = _get_html(session, url, timeout=10.0)
        except req_exc.RequestException as exc:
            logger.warning("THS board fetch failed kind=%s url=%s: %s", ths_kind, url, exc)
            return []
        return _parse_board_index_html(html, ths_kind=ths_kind, source_label=label)

    page = 1
    while len(out) < limit and page <= max_pages:
        batch = _collect_from_url(_index_ajax_url(ths_kind, page))
        if not batch and page == 1:
            batch = _collect_from_url(_index_ajax_url_detail_fallback(ths_kind, page))
        if not batch:
            break
        out.extend(batch)
        page += 1
        time.sleep(0.25)

    if not out:
        out = _collect_from_url(_index_page_url(ths_kind))
    return out


def _fetch_board_index(ths_kind: ThsBoardKind, *, limit: int, session: requests.Session | None = None) -> list[dict[str, Any]]:
    meta = _KIND_META[ths_kind]
    label = meta["label"]
    path = meta["path"]

    # concept/industry：akshare 优先；region/csrc 无 akshare 接口，直接抓取
    if ths_kind in ("concept", "industry"):
        out = _fetch_board_index_akshare(ths_kind, limit=limit, source_label=label)
        if out:
            return out[:limit]

    session = session or _new_session(referer_path=path)
    out = _scrape_board_pages(ths_kind, limit=limit, session=session, label=label)

    if not out and ths_kind in ("concept", "industry"):
        out = _fetch_board_index_akshare(ths_kind, limit=limit, source_label=label)

    dedup: dict[str, dict[str, Any]] = {}
    for row in out:
        dedup[str(row["sector_code"])] = row
    out = list(dedup.values())
    out.sort(key=lambda x: x["change_pct"], reverse=True)
    return out[:limit]


def _fetch_members_scrape(
    sector_code: str,
    ths_kind: ThsBoardKind,
    *,
    limit: int,
    session: requests.Session | None = None,
) -> list[dict[str, Any]]:
    code = str(sector_code or "").strip()
    if not code:
        return []
    path = _KIND_META[ths_kind]["path"]
    session = session or _new_session(referer_path=path)
    members: list[dict[str, Any]] = []
    page = 1
    while len(members) < limit and page <= 8:
        url = _members_ajax_url(ths_kind, code, page)
        try:
            html = _get_html(session, url)
        except req_exc.RequestException as exc:
            logger.warning("THS members failed kind=%s code=%s: %s", ths_kind, code, exc)
            break
        batch = _parse_members_html(html)
        if not batch:
            break
        members.extend(batch)
        page += 1
        time.sleep(0.35)
    members.sort(key=lambda x: x["change_pct"], reverse=True)
    return members[:limit]


def _fetch_members_akshare(sector_name: str, ths_kind: ThsBoardKind, *, limit: int) -> list[dict[str, Any]]:
    if ths_kind not in ("concept", "industry"):
        return []
    try:
        import akshare as ak
    except ImportError:
        return []

    name = (sector_name or "").strip()
    if not name:
        return []

    try:
        if ths_kind == "concept":
            df = ak.stock_board_concept_cons_ths(symbol=name)
        else:
            fn = getattr(ak, "stock_board_industry_cons_ths", None)
            if fn is None:
                return []
            df = fn(symbol=name)
    except Exception as exc:
        logger.warning("akshare THS members failed name=%s: %s", name, exc)
        return []

    members: list[dict[str, Any]] = []
    for _, row in df.head(limit).iterrows():
        sym6 = str(row.get("代码") or row.get("code") or "").zfill(6)[-6:]
        if len(sym6) != 6:
            continue
        market = "bj" if sym6.startswith(("4", "8")) else ("sh" if sym6.startswith(("5", "6", "9")) else "sz")
        pct_raw = row.get("涨跌幅") or row.get("涨跌幅(%)") or 0
        try:
            change_pct = float(str(pct_raw).replace("%", ""))
        except ValueError:
            change_pct = 0.0
        members.append(
            {
                "symbol": f"{market}{sym6}",
                "code": sym6,
                "name": str(row.get("名称") or row.get("name") or ""),
                "change_pct": change_pct,
                "price": 0.0,
                "amount": 0.0,
                "volume": 0.0,
            }
        )
    return members


def fetch_ths_concept_boards(*, limit: int = 80, session: requests.Session | None = None) -> list[dict[str, Any]]:
    """同花顺概念板块（https://q.10jqka.com.cn/gn/）。"""
    return _fetch_board_index("concept", limit=limit, session=session)


def fetch_ths_region_boards(*, limit: int = 80, session: requests.Session | None = None) -> list[dict[str, Any]]:
    """同花顺地域板块（https://q.10jqka.com.cn/dy/）。"""
    return _fetch_board_index("region", limit=limit, session=session)


def fetch_ths_industry_boards(*, limit: int = 80, session: requests.Session | None = None) -> list[dict[str, Any]]:
    """同花顺行业板块（https://q.10jqka.com.cn/thshy/）。"""
    return _fetch_board_index("industry", limit=limit, session=session)


def fetch_ths_csrc_boards(*, limit: int = 80, session: requests.Session | None = None) -> list[dict[str, Any]]:
    """同花顺证监会行业（https://q.10jqka.com.cn/zjhhy/）。"""
    return _fetch_board_index("csrc", limit=limit, session=session)


def fetch_ths_all_boards(*, limit_per_kind: int = 160, session: requests.Session | None = None) -> list[dict[str, Any]]:
    """四类同花顺板块榜单合并（概念/地域/行业/证监会）。"""
    from concurrent.futures import ThreadPoolExecutor, as_completed

    cap = max(1, min(int(limit_per_kind or 60), 120))
    rows: list[dict[str, Any]] = []
    kinds: tuple[ThsBoardKind, ...] = ("concept", "region", "industry", "csrc")
    # requests.Session 非线程安全；并行时各任务自建 session
    shared = session if len(kinds) == 1 else None

    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {
            pool.submit(_fetch_board_index, kind, limit=cap, session=shared): kind
            for kind in kinds
        }
        for fut in as_completed(futures, timeout=20):
            kind = futures[fut]
            try:
                rows.extend(fut.result())
            except Exception as exc:
                logger.warning("THS fetch_all kind=%s failed: %s", kind, exc)
    return rows


def normalize_ths_board_kind(board_kind: str | None) -> ThsBoardKind:
    k = (board_kind or "concept").strip().lower()
    if k in ("region", "dy", "地域", "area"):
        return "region"
    if k in ("csrc", "zjhhy", "证监会", "证监会行业"):
        return "csrc"
    if k in ("industry", "thshy", "行业", "hangye"):
        return "industry"
    return "concept"


def fetch_ths_board_members(
    sector_code: str,
    *,
    kind: ThsBoardKind | str = "concept",
    sector_name: str | None = None,
    limit: int = 80,
    session: requests.Session | None = None,
) -> list[dict[str, Any]]:
    """同花顺板块成分股（页面抓取，概念/行业可用 AkShare 名称兜底）。"""
    ths_kind = kind if kind in _KIND_META else normalize_ths_board_kind(str(kind))
    rows = _fetch_members_scrape(sector_code, ths_kind, limit=limit, session=session)
    if rows:
        return rows
    if sector_name:
        rows = _fetch_members_akshare(sector_name, ths_kind, limit=limit)
    return rows


def is_ths_sector_code(sector_code: str) -> bool:
    """东财 BK / 开盘啦 801·881·885 / 选股通长 ID 排除；同花顺为数字或证监会字母码。"""
    code = (sector_code or "").strip().upper()
    if not code or code.startswith("BK"):
        return False
    if code.startswith(("801", "881", "885")) and len(code) == 6:
        return False
    if code.isdigit() and len(code) >= 7:
        return False
    if re.fullmatch(r"[A-Z]{1,3}", code):
        return True
    digits = "".join(ch for ch in code if ch.isdigit())
    return 5 <= len(digits) <= 6

if __name__ == "__main__":
    fetch_ths_all_boards()
