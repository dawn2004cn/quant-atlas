"""阶段 3：预测注册表与选股数据源（轻量单测）。"""

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from app.application.services.model_predict_lab_service import ModelPredictLabService
from app.application.services.prediction_service import PredictionApplicationService
from app.application.services.qlib_pipeline_service import QlibPipelineService
from app.application.services.selection_source_service import SelectionSourceService
from app.application.services.strategy_service import StrategyApplicationService
from app.domain.enums import MarketCode


def test_prediction_list_models_seeds_registry(tmp_path: Path):
    m = MagicMock()
    pred_lab = ModelPredictLabService(m)
    svc = PredictionApplicationService(pred_lab, base_dir=tmp_path)
    models = svc.list_models()
    assert any(str(x.get("id")) == "default_momentum" for x in models)
    reg = tmp_path / "config" / "model_registry.json"
    assert reg.is_file()
    data = json.loads(reg.read_text(encoding="utf-8"))
    assert "models" in data


def test_selection_legacy_delegates_to_strategy(tmp_path: Path):
    strat = MagicMock(spec=StrategyApplicationService)
    strat.select_stocks.return_value = {
        "candidates": [{"code": "600519", "score": 80}],
        "sentiment_analysis": {},
        "strategy": "classic",
        "market": "CN",
        "generated_at": "",
        "effective_strategy_group": "classic",
    }
    qlib = MagicMock(spec=QlibPipelineService)
    pred_lab = ModelPredictLabService(MagicMock())
    pred_app = PredictionApplicationService(pred_lab, base_dir=tmp_path)
    mkt = MagicMock()
    mkt.list_quotes.return_value = []
    sel = SelectionSourceService(strat, qlib, pred_app, mkt)
    out = sel.select_stocks(
        strategy="classic",
        market=MarketCode.CN,
        top_n=5,
        data_source="legacy",
        enable_qlib=False,
    )
    assert out["candidates"][0]["code"] == "600519"
    strat.select_stocks.assert_called_once()


def test_cross_section_factor_rank_empty_universe(tmp_path: Path):
    m = MagicMock()
    m.get_stock_history.return_value = []
    from app.modules.system.services.tools.tool_facade_service import ToolFacadeService

    access = ToolFacadeService(market_provider=m, stock_service=None, archive=None, fundamental_provider=None, strategy_service=None)
    pipe = QlibPipelineService(access, base_dir=tmp_path)
    out = pipe.cross_section_factor_rank(MarketCode.CN, top_n=5)
    assert out.get("error") == "no_instruments"
