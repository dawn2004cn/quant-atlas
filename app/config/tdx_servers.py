from __future__ import annotations

"""Default TDX (通达信) server lists.

These are public stock exchange data servers, not secrets.
The defaults work for most users. Override via TDX_SERVERS_JSON env var.
"""

import json
import os
from typing import Any
import logging
logger = logging.getLogger(__name__)



# TDX HQ (行情) server pool
_DEFAULT_TDX_SERVERS: list[dict[str, Any]] = [
    {"name": "首登信息更新专用通道5", "ip": "123.125.108.216", "port": 7709, "ms": 277.54},
    {"name": "云行情广州主站Z1", "ip": "45.116.35.251", "port": 7709, "ms": 510.61},
    {"name": "(中信)短线宝21", "ip": "58.67.221.146", "port": 7709, "ms": 655.05},
    {"name": "广州联通主站Z1", "ip": "210.21.65.136", "port": 7709, "ms": 697.23},
    {"name": "(中信)短线宝23", "ip": "115.238.90.170", "port": 7709, "ms": 704.65},
    {"name": "(中信)短线宝1", "ip": "180.153.18.170", "port": 7709, "ms": 717.35},
    {"name": "次登即时决策更新专用通道10", "ip": "116.57.224.5", "port": 7709, "ms": 734.81},
    {"name": "(中信)短线宝20", "ip": "58.67.221.146", "port": 7709, "ms": 752.31},
    {"name": "广州电信主站Z1", "ip": "121.33.228.164", "port": 7709, "ms": 754.76},
    {"name": "次登即时决策更新专用通道8", "ip": "39.105.251.234", "port": 7709, "ms": 793.53},
    {"name": "上海电信主站Z80", "ip": "180.153.18.172", "port": 80, "ms": 826.17},
    {"name": "(中信)短线宝17", "ip": "60.12.136.250", "port": 7709, "ms": 858.85},
    {"name": "次登即时决策更新专用通道1", "ip": "39.108.28.83", "port": 7709, "ms": 896.63},
    {"name": "上海电信主站Z1", "ip": "180.153.18.170", "port": 7709, "ms": 897.94},
    {"name": "上海电信主站Z4", "ip": "58.34.106.207", "port": 7709, "ms": 922.11},
    {"name": "杭州电信主站J3", "ip": "218.75.126.9", "port": 7709, "ms": 941.53},
    {"name": "南京移动主站Z1", "ip": "221.131.136.194", "port": 7709, "ms": 956.39},
    {"name": "杭州移动主站J2", "ip": "120.199.2.123", "port": 7709, "ms": 968.17},
    {"name": "杭州电信主站J1", "ip": "60.191.117.167", "port": 7709, "ms": 980.97},
    {"name": "南京电信主站Z1", "ip": "61.147.174.2", "port": 7709, "ms": 1012.49},
    {"name": "北京联通主站Z80", "ip": "202.108.253.139", "port": 80, "ms": 1029.05},
    {"name": "北京移动主站Z1", "ip": "111.13.112.206", "port": 7709, "ms": 1048.40},
    {"name": "北京联通主站Z2", "ip": "202.108.254.67", "port": 7709, "ms": 1050.12},
    {"name": "上海移动主站Z1", "ip": "120.253.221.207", "port": 7709, "ms": 1061.75},
    {"name": "南京联通主站Z1", "ip": "218.98.6.162", "port": 7709, "ms": 1077.34},
    {"name": "杭州电信主站J2", "ip": "115.238.56.198", "port": 7709, "ms": 1079.35},
    {"name": "(中信)短线宝22", "ip": "60.12.136.251", "port": 7709, "ms": 1097.76},
    {"name": "杭州移动主站J1", "ip": "120.199.2.122", "port": 7709, "ms": 1100.04},
    {"name": "杭州电信主站J4", "ip": "115.238.90.165", "port": 7709, "ms": 1120.22},
    {"name": "北京联通主站Z1", "ip": "202.108.254.67", "port": 7709, "ms": 1124.91},
    {"name": "杭州移动主站J3", "ip": "117.149.2.68", "port": 7709, "ms": 1192.12},
    {"name": "杭州移动主站J4", "ip": "117.149.2.70", "port": 7709, "ms": 1198.91},
    {"name": "再登短线宝等综合更新专用通道1", "ip": "180.153.18.170", "port": 7709, "ms": 1219.92},
    {"name": "首登信息更新专用通道1", "ip": "175.6.5.131", "port": 7709, "ms": 1250.34},
    {"name": "北京联通主站Z802", "ip": "202.108.253.158", "port": 80, "ms": 1290.20},
    {"name": "杭州联通主站J2", "ip": "60.12.136.250", "port": 7709, "ms": 1419.60},
    {"name": "云行情沈阳主站Z2", "ip": "42.177.92.37", "port": 7709, "ms": 1520.34},
    {"name": "云行情上海金桥主站Z1", "ip": "114.141.177.44", "port": 7709, "ms": 2131.09},
    {"name": "云行情郑州主站Z2", "ip": "182.118.8.4", "port": 7709, "ms": 2847.17},
    {"name": "云行情福州主站Z1", "ip": "27.151.2.37", "port": 7709, "ms": 3010.63},
]

# TDX Extended Market (扩展市场) server pool
_DEFAULT_TDX_EX_SERVERS: list[dict[str, Any]] = [
    {"name": "扩展市场广州双线1", "ip": "116.205.143.214", "port": 7727, "ms": 66.67},
    {"name": "扩展市场上海双线2", "ip": "47.102.108.214", "port": 7727, "ms": 107.21},
    {"name": "扩展市场深圳双线2", "ip": "120.25.218.6", "port": 7727, "ms": 3043.70},
    {"name": "扩展市场深圳双线1", "ip": "112.74.214.43", "port": 7727, "ms": 3046.81},
]


def _load_servers(env_var: str, default: list[dict[str, Any]]) -> list[dict[str, Any]]:
    raw = os.environ.get(env_var)
    if raw:
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                return parsed
        except (json.JSONDecodeError, TypeError):
            logger.warning("Suppressed exception", exc_info=True)
            pass
    return default


def get_tdx_servers() -> list[dict[str, Any]]:
    """Return HQ server list, overridable via TDX_SERVERS_JSON."""
    return _load_servers("TDX_SERVERS_JSON", _DEFAULT_TDX_SERVERS)


def get_tdx_ex_servers() -> list[dict[str, Any]]:
    """Return extended market server list, overridable via TDX_EX_SERVERS_JSON."""
    return _load_servers("TDX_EX_SERVERS_JSON", _DEFAULT_TDX_EX_SERVERS)
