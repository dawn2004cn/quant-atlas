"""
龙虎榜明细入库 CLI（已迁入 ``app.cli``）。

推荐：自仓库根目录执行::

    python -m app.cli longhu [--lookback-days 14]

等价于调用 ``BasicMarketDataService.ingest_longhu_em``（写入 ``instance/basic_market_data.db``）。
Web：``/longhu-bang``；API：``GET /api/v1/market/longhu``；Agent：``get_cn_longhu_for_symbol``。
"""

from __future__ import annotations

import sys
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


if __name__ == "__main__":
    root = _repo_root()
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    from app.cli.main import main

    sys.exit(main(["longhu", *sys.argv[1:]]))
