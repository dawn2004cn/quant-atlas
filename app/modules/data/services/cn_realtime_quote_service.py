from __future__ import annotations
from app.domain.dto.service_result import GenericResponseDTO
"""A 股实时行情：优先通达??Pytdx，缺失时回退腾讯 HTTP??"""


from typing import Any

from app.core.logger import get_logger
from app.domain.enums import MarketCode
from app.modules.market_data.services.cn_quote_snapshot import get_cn_quote_snapshot
from app.domain.shared.symbol_normalizer import SymbolNormalizer
from app.modules.system.services.helpers.pytdx_access import get_pytdx_market_port
from app.domain.shared.pytdx_quote_mapper import pytdx_row_to_quote_payload

logger = get_logger(__name__)

_QUOTE_CHUNK = 80


def _symbol_index_keys(symbol: str) -> list[str]:
    raw = str(symbol or "").strip()
    if not raw:
        return []
    norm = raw.split(":", 1)[1] if ":" in raw else raw
    keys = {raw, norm, norm.lower()}
    if norm.lower().startswith(("sh", "sz", "bj")):
        keys.add(norm[2:])
    digits = "".join(ch for ch in norm if ch.isdigit())[-6:].zfill(6)
    if digits and digits != "000000":
        keys.add(digits)
    return list(keys)


def _index_payload(out: dict[str, dict[str, Any]], payload: dict[str, Any]) -> None:
    for key in _symbol_index_keys(str(payload.get("code") or "")):
        out[key] = payload


class CnRealtimeQuoteService:
    """批量拉取 A 股实时行情并建立多键索引?? ??/ shsz 前缀）??"""

    _pytdx_warmed: bool = False

    def __init__(self, *, market_provider: object | None = None) -> None:
        self._market_provider = market_provider
        self._normalizer = SymbolNormalizer()

    def fetch_map(
        self,
        symbols: list[str],
        *,
        prefer_tdx: bool = True,
    ) -> GenericResponseDTO[str, dict[str, Any]]:
        if not symbols:
            return {}

        norm_list: list[str] = []
        seen: set[str] = set()
        for sym in symbols:
            try:
                n = self._normalizer.normalize(sym)
            except Exception:
                n = str(sym).strip()
            if n and n not in seen:
                seen.add(n)
                norm_list.append(n)

        out: dict[str, dict[str, Any]] = {}
        snap = get_cn_quote_snapshot()
        snap_hits, missing = snap.lookup_map(norm_list)
        out.update(snap_hits)

        if not missing:
            return out

        tdx_syms, non_tdx_syms = self._split_for_pytdx(missing)
        still_missing: list[str] = list(non_tdx_syms)
        if prefer_tdx and tdx_syms and get_pytdx_market_port().is_available():
            self._ensure_pytdx_warm()
            still_missing.extend(self._fetch_pytdx(tdx_syms, out))

        if still_missing:
            self._fetch_tencent(still_missing, out)

        return out

    @staticmethod
    def _split_for_pytdx(norm_list: list[str]) -> tuple[list[str], list[str]]:
        """Pytdx 标准行情仅稳定覆盖沪??A 股；北交所等走腾讯回退??"""
        tdx_syms: list[str] = []
        other: list[str] = []
        for n in norm_list:
            low = n.lower()
            digits = "".join(ch for ch in low if ch.isdigit())
            if low.startswith("bj") or (digits.startswith("92") and len(digits) >= 6):
                other.append(n)
            else:
                tdx_syms.append(n)
        return tdx_syms, other

    @staticmethod
    def _ensure_pytdx_warm() -> None:
        """首次连接通达信行情服务器约需数秒，后台预热避免首屏卡顿??"""
        if CnRealtimeQuoteService._pytdx_warmed:
            return
        try:
            from app.modules.data.services.pytdx_market_data_service import (
                get_pytdx_market_data_service,
            )

            get_pytdx_market_data_service().get_quotes(["600519"])
            CnRealtimeQuoteService._pytdx_warmed = True
        except Exception as exc:
            logger.debug("pytdx warm-up skipped: %s", exc)

    def _fetch_pytdx(
        self,
        norm_list: list[str],
        out: dict[str, dict[str, Any]],
    ) -> list[str]:
        """返回仍未命中??normalized symbol 列表??"""
        try:
            from app.modules.data.services.pytdx_market_data_service import (
                get_pytdx_market_data_service,
            )

            rows = get_pytdx_market_data_service().get_quotes(norm_list)
        except Exception as exc:
            logger.warning("cn quotes pytdx failed: %s", exc)
            return norm_list

        for row in rows:
            if not isinstance(row, dict):
                continue
            payload = pytdx_row_to_quote_payload(row)
            if payload.get("code"):
                _index_payload(out, payload)

        missing: list[str] = []
        for n in norm_list:
            keys = _symbol_index_keys(n)
            if not any(k in out for k in keys):
                missing.append(n)
        return missing

    def _fetch_tencent(
        self,
        norm_list: list[str],
        out: dict[str, dict[str, Any]],
    ) -> None:
        provider = self._market_provider
        if provider is None:
            from app.modules.system.services.helpers.market_data_provider import get_market_data_provider

            provider = get_market_data_provider()

        for i in range(0, len(norm_list), _QUOTE_CHUNK):
            chunk = norm_list[i : i + _QUOTE_CHUNK]
            try:
                if hasattr(provider, "get_realtime_quotes"):
                    raw = provider.get_realtime_quotes(chunk, market=MarketCode.CN) or []
                elif hasattr(provider, "get_quotes"):
                    raw = provider.get_quotes(chunk, market=MarketCode.CN) or []
                else:
                    raw = []
            except Exception as exc:
                logger.warning("cn quotes tencent chunk failed: %s", exc)
                continue

            for q in raw:
                payload = self._entity_to_payload(q)
                if payload.get("code"):
                    payload["source"] = payload.get("source") or "tencent"
                    _index_payload(out, payload)

    @staticmethod
    def _entity_to_payload(q: object) -> GenericResponseDTO:
        if isinstance(q, dict):
            row = dict(q)
        else:
            row = {
                "code": getattr(q, "code", "") or "",
                "name": getattr(q, "name", "") or "",
                "price": float(getattr(q, "price", 0) or 0),
                "change_pct": float(getattr(q, "change_pct", 0) or 0),
                "change_amount": float(getattr(q, "change_amount", 0) or 0),
                "volume": float(getattr(q, "volume", 0) or 0),
                "amount": float(getattr(q, "amount", 0) or 0),
                "turnover": float(getattr(q, "turnover", 0) or 0),
                "volume_ratio": float(getattr(q, "volume_ratio", 0) or 0),
                "amplitude": float(getattr(q, "amplitude", 0) or 0),
                "pe": float(getattr(q, "pe", 0) or 0),
                "pb": float(getattr(q, "pb", 0) or 0),
                "industry": getattr(q, "industry", "") or "",
            }
        code = str(row.get("code") or "")
        norm = code.split(":", 1)[1] if ":" in code else code
        row["code"] = norm
        return row
