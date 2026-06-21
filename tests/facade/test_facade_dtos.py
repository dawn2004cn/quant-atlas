"""Facade DTO validation and normalization tests."""

from __future__ import annotations

import pytest
from pydantic import ValidationError as PydanticValidationError

from app.facade.dto.ai_facade_dto import AIAnalysisRequestDTO, AIAnalysisResultDTO
from app.facade.dto.backtest_facade_dto import BacktestResultDTO
from app.facade.dto.market_facade_dto import HistoryBarsQueryDTO


def test_history_bars_query_normalizes_symbol():
    dto = HistoryBarsQueryDTO(symbol=" 600519 ", market="CN")
    assert dto.symbol == "600519"


def test_history_bars_query_rejects_inverted_range():
    with pytest.raises(PydanticValidationError):
        HistoryBarsQueryDTO(
            symbol="600519",
            market="CN",
            start_date="2024-06-01",
            end_date="2024-01-01",
        )


def test_backtest_result_maps_metric_aliases():
    dto = BacktestResultDTO.from_service(
        {
            "status": "ok",
            "sharpe_ratio": 1.1,
            "max_drawdown_pct": -0.12,
            "winrate": 0.48,
            "equity": [{"date": "2024-01-01", "value": 1.0}],
        }
    )
    assert dto.sharpe == 1.1
    assert dto.max_drawdown == -0.12
    assert dto.win_rate == 0.48
    assert len(dto.equity_curve) == 1


def test_backtest_result_derives_max_drawdown_pct():
    dto = BacktestResultDTO.from_service(
        {"status": "ok", "max_drawdown": -0.085, "sharpe": 0.5}
    )
    assert dto.max_drawdown == -0.085
    assert dto.max_drawdown_pct == 8.5


def test_ai_analysis_request_rejects_empty_symbol():
    with pytest.raises(PydanticValidationError):
        AIAnalysisRequestDTO(symbol="   ", market="CN")


def test_ai_analysis_result_extracts_evidence_and_prompt_trace():
    dto = AIAnalysisResultDTO.from_service(
        {
            "symbol": "600519",
            "market": "CN",
            "ai": {
                "summary": "neutral",
                "confidence": 0.6,
                "prompt_hash": "abc123",
                "risk_flags": ["high_volatility"],
            },
            "decision": {
                "evidence": [{"source": "news", "text": "earnings beat"}],
            },
            "decision_id": "dec-1",
        }
    )
    assert dto.conclusion == "neutral"
    assert dto.confidence == 0.6
    assert dto.prompt_trace["prompt_hash"] == "abc123"
    assert dto.risk_flags == ["high_volatility"]
    assert dto.evidence[0]["source"] == "news"
    assert dto.decision_id == "dec-1"
