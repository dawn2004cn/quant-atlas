from __future__ import annotations

from unittest.mock import MagicMock, patch

from pydantic import BaseModel, Field

from app.presentation.api.dto_validation import validate_request


class _HistoryReq(BaseModel):
    start: str = Field(...)
    end: str = Field(...)
    max_points: int = Field(default=0, ge=0)


def test_validate_request_injects_req_kwarg_for_path_params() -> None:
    @validate_request(_HistoryReq, source="args")
    def handler(market: str, symbol: str, req: _HistoryReq):
        return market, symbol, req

    mock_request = MagicMock()
    mock_request.args.to_dict.return_value = {
        "start": "2024-03-28",
        "end": "2026-06-06",
        "max_points": "1421",
    }
    with patch("flask.request", mock_request):
        market, symbol, req = handler(market="CN", symbol="sz000338")
    assert market == "CN"
    assert symbol == "sz000338"
    assert req.start == "2024-03-28"
    assert req.max_points == 1421
