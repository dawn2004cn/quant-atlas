"""QlibService 工具函数（不依赖 qlib 数据目录）。"""

import pandas as pd

from app.modules.data.services.qlib_service import QlibService


def test_platform_signal_rows_from_dataframe():
    df = pd.DataFrame(
        {
            "Date": pd.to_datetime(["2024-01-02", "2024-01-03"]),
            "Close": [10.0, 10.5],
            "Signal": [1, 0],
        }
    )
    rows = QlibService.platform_signal_rows_from_dataframe(df, instrument="SH600519")
    assert len(rows) == 2
    assert rows[0]["Signal"] == 1
    assert rows[0]["date"] == "2024-01-02"


def test_integrate_builds_preview_without_backtest():
    svc = QlibService()
    out = svc.integrate_existing_strategy(
        {
            "records": [
                {"date": "2024-01-02", "Signal": 1},
                {"date": "2024-01-03", "Signal": -1},
            ],
            "instrument": "SH600519",
        }
    )
    assert out["ok"] is True
    assert out["points"] == 2
    assert out["preview"]
