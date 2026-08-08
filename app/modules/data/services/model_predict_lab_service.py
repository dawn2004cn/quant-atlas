from __future__ import annotations
from app.domain.dto.service_result import GenericResponseDTO
"""中长线排序预测占位实现：统一接口供后续接入 LGBModel / LSTM。"""


from typing import Any

import pandas as pd

from app.domain.enums import MarketCode
from app.domain.ports import MarketDataProvider


class ModelPredictLabService:
    def __init__(self, market_provider: MarketDataProvider) -> None:
        self._market = market_provider

    def predict_rank(
        self,
        *,
        symbols: list[str],
        market: MarketCode,
        model_id: str,
        horizon_days: int = 20,
    ) -> GenericResponseDTO:
        """按中期动量（N 日收益）排序；``model_id`` 仅影响展示标签，算法可后续分叉。"""
        h = max(5, min(int(horizon_days or 20), 250))
        mid = (model_id or "lgbm").strip().lower()
        rows: list[dict[str, Any]] = []
        end = pd.Timestamp.today().strftime("%Y-%m-%d")
        start = (pd.Timestamp.today() - pd.Timedelta(days=h + 120)).strftime("%Y-%m-%d")

        for sym in symbols:
            s = str(sym).strip()
            if not s:
                continue
            hist = self._market.get_stock_history(s, market, start, end)
            if not hist:
                rows.append(
                    {
                        "symbol": s,
                        "score": None,
                        "horizon_return_pct": None,
                        "bars_used": 0,
                        "ok": False,
                        "note": "无K线",
                    }
                )
                continue
            df = pd.DataFrame(hist)
            col_map = {c.lower(): c for c in df.columns}
            close_col = col_map.get("close", "close")
            if close_col not in df.columns:
                rows.append({"symbol": s, "score": None, "horizon_return_pct": None, "bars_used": 0, "ok": False, "note": "缺 close"})
                continue
            closes = pd.to_numeric(df[close_col], errors="coerce").dropna()
            if len(closes) < h + 1:
                rows.append(
                    {
                        "symbol": s,
                        "score": None,
                        "horizon_return_pct": None,
                        "bars_used": int(len(closes)),
                        "ok": False,
                        "note": f"样本不足(需>{h})",
                    }
                )
                continue
            last = float(closes.iloc[-1])
            base = float(closes.iloc[-1 - h])
            ret = (last / base - 1.0) * 100.0 if base else 0.0
            rows.append(
                {
                    "symbol": s,
                    "score": round(ret, 4),
                    "horizon_return_pct": round(ret, 4),
                    "bars_used": int(len(closes)),
                    "ok": True,
                    "note": "",
                }
            )

        ok_rows = [r for r in rows if r.get("ok")]
        ok_rows.sort(key=lambda x: float(x.get("score") or 0.0), reverse=True)
        bad_rows = [r for r in rows if not r.get("ok")]
        ranking = ok_rows + bad_rows

        label = "LightGBM（启发式动量）" if "lgb" in mid else "LSTM（启发式动量）" if "lstm" in mid else f"模型({model_id})启发式动量"
        return {
            "ranking": ranking,
            "model_id": model_id,
            "horizon_days": h,
            "source": "heuristic_momentum",
            "model_label": label,
            "evidence": f"按最近 {h} 个交易日收盘收益排序；非已训练模型输出，接入 Qlib 模型后可切换 source。",
        }
