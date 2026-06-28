from __future__ import annotations

"""Symbol normalizer — A 股等平台统一代码格式（canonical: sh600519）。"""


import re

_LEGACY_MARKET_PREFIXES = frozenset({"cn", "hk", "us", "crypto"})


class SymbolNormalizer:
    """跨数据源股票代码规范化；A 股存储与 API 统一为 sh/sz/bj + 6 位。"""

    def __init__(self) -> None:
        self._mapping: dict[str, str] = {}
        self._load_default_mappings()

    def _load_default_mappings(self) -> None:
        self._mapping = {
            "600000": "sh600000",
            "600001": "sh600001",
            "000001": "sz000001",
            "000002": "sz000002",
            "300001": "sz300001",
            "688001": "sh688001",
        }

    def normalize(self, symbol: str) -> str:
        if not symbol:
            return ""
        s_upper = str(symbol).strip().upper()
        if s_upper in self._mapping:
            return self._mapping[s_upper]
        return self.normalize_cn_symbol(symbol)

    def to_tdx(self, symbol: str) -> str:
        return self.normalize(symbol).upper()

    def to_eastmoney(self, symbol: str) -> str:
        normalized = self.normalize(symbol)
        if normalized.startswith(("sh", "sz", "bj")):
            return normalized[2:]
        return symbol

    @staticmethod
    def _strip_legacy_uid(symbol: str) -> str:
        """移除 ``CN:`` / ``HK:`` 等遗留 UID 前缀（大小写不敏感）。"""
        s = str(symbol or "").strip()
        if ":" not in s:
            return s
        head, rest = s.split(":", 1)
        if head.lower() in _LEGACY_MARKET_PREFIXES:
            return rest.strip()
        return s

    @staticmethod
    def normalize_cn_symbol(symbol: str) -> str:
        """A 股规范码：``sh600519`` / ``sz000001`` / ``bj830001``。"""
        if not symbol:
            return ""

        s = SymbolNormalizer._strip_legacy_uid(symbol).strip().lower()

        if "." in s:
            code, market = s.split(".", 1)
            if market in ("sh", "ss"):
                return f"sh{code.zfill(6)}"
            if market in ("sz",):
                return f"sz{code.zfill(6)}"
            if market in ("bj",):
                return f"bj{code.zfill(6)}"
            s = code

        if s.startswith(("sh", "sz", "bj")):
            market = s[:2]
            code = s[2:]
            return f"{market}{code.zfill(6)}"

        code = "".join(ch for ch in s if ch.isdigit())
        if len(code) >= 6:
            code = code[-6:].zfill(6)
        else:
            code = s.zfill(6) if s.isdigit() else s

        if not code.isdigit() or len(code) != 6:
            return s

        if code.startswith("6"):
            return f"sh{code}"
        if code.startswith(("0", "3")):
            return f"sz{code}"
        if code.startswith(("8", "4", "9")):
            return f"bj{code}"
        return f"sz{code}"

    @staticmethod
    def to_db_code(symbol: str, market: str = "CN") -> str:
        """数据库 / API 标准 A 股代码（``sh600519``，无 ``CN:``）。"""
        _ = market  # 保留参数兼容旧调用
        return SymbolNormalizer.normalize_cn_symbol(symbol)

    @staticmethod
    def from_db_code(symbol: str) -> str:
        return SymbolNormalizer.to_db_code(symbol)

    @staticmethod
    def to_api_code(symbol: str) -> str:
        return SymbolNormalizer.to_db_code(symbol)

    @staticmethod
    def normalized_with_prefix(symbol: str) -> str:
        return SymbolNormalizer.to_db_code(symbol)

    @staticmethod
    def to_full_code(symbol: str) -> str:
        return SymbolNormalizer.to_db_code(symbol)

    @staticmethod
    def to_code6(symbol: str) -> str:
        return SymbolNormalizer.normalize_code(symbol)

    @staticmethod
    def to_display(symbol: str) -> str:
        code6 = SymbolNormalizer.normalize_code(symbol)
        mid = SymbolNormalizer.market_id(symbol)
        if mid == 1:
            return f"沪A{code6}"
        if mid == 2:
            return f"北A{code6}"
        return f"深A{code6}"

    @staticmethod
    def is_valid(symbol: str) -> bool:
        cn = SymbolNormalizer.to_db_code(symbol)
        if not re.fullmatch(r"(sh|sz|bj)\d{6}", cn):
            return False
        code6 = cn[2:]
        return code6 != "000000"

    @staticmethod
    def parse_input(symbol: str) -> dict[str, str]:
        cn_symbol = SymbolNormalizer.to_db_code(symbol)
        code6 = SymbolNormalizer.normalize_code(cn_symbol)
        market = cn_symbol[:2] if cn_symbol.startswith(("sh", "sz", "bj")) else "sz"
        return {
            "code6": code6,
            "market": market,
            "cn_symbol": cn_symbol,
            "db_code": cn_symbol,
            "display": SymbolNormalizer.to_display(cn_symbol),
        }

    @staticmethod
    def market_id(symbol: str) -> int:
        s = SymbolNormalizer._strip_legacy_uid(symbol).lower()
        if s.startswith("sh"):
            return 1
        if s.startswith("sz"):
            return 0
        if s.startswith("bj"):
            return 2

        code = SymbolNormalizer.normalize_code(s)
        if code.startswith(("6", "5", "11")):
            return 1
        if code.startswith(("0", "3", "2")):
            return 0
        if code.startswith(("9", "8", "4")):
            return 2
        return 0

    @staticmethod
    def normalize_code(symbol: str) -> str:
        if not symbol:
            return ""
        s = SymbolNormalizer._strip_legacy_uid(symbol).strip().lower()
        if s.startswith(("sh", "sz", "bj")):
            s = s[2:]
        elif "." in s:
            s = s.split(".", 1)[0]
        match = re.search(r"(\d{6})", s)
        if match:
            return match.group(1)
        return s.zfill(6)[-6:] if s.isdigit() else s.zfill(6)[-6:]


_default_normalizer: SymbolNormalizer | None = None


def get_symbol_normalizer() -> SymbolNormalizer:
    global _default_normalizer
    if _default_normalizer is None:
        _default_normalizer = SymbolNormalizer()
    return _default_normalizer


__all__ = ["SymbolNormalizer", "get_symbol_normalizer"]
