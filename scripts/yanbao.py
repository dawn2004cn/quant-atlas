"""
东方财富研报列表入库 CLI（已迁入 ``app.cli``）。

推荐：自仓库根目录执行::

    python -m app.cli yanbao

等价于调用 ``BasicMarketDataService.ingest_yanbao_eastmoney_html``（写入 ``instance/basic_market_data.db``）。
Web：``/yanbao-hub``；API：``GET /api/v1/market/yanbao``；Agent：``get_yanbao_market_digest``。
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

    sys.exit(main(["yanbao", *sys.argv[1:]]))
