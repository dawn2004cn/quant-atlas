"""Lifecycle route envelope + market panorama cache tests."""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from app.domain.enums import MarketCode
from app.presentation.api.responses import success_response
from tests.helpers import create_test_app


def test_success_response_canonical_envelope():
    app = create_test_app()
    with app.app_context():
        resp, status = success_response(data={"count": 3})
    assert status == 200
    payload = json.loads(resp.get_data(as_text=True))
    assert payload["success"] is True
    assert payload["ok"] is True
    assert payload["status"] == "success"
    assert payload["data"] == {"count": 3}
    assert payload["error"] is None


@patch("app.modules.market_data.services.market_service.get_quote_cache_port")
def test_market_panorama_uses_cache_on_second_call(mock_get_quote_cache_port):
    from app.modules.market_data.services.market_service import MarketApplicationService

    mock_get_quote_cache_port.return_value = MagicMock()
    provider = MagicMock()
    provider.get_market_overview.return_value = {"market_status": "open", "sentiment_score": 55.0}
    provider.get_market_rankings.return_value = {
        "gainers": [{"code": "600519", "name": "Moutai", "change_pct": 2.1}],
        "losers": [],
        "amounts": [],
        "turnovers": [],
    }
    stored: dict[str, object] = {}
    cache = MagicMock()

    def _get_or_set(key: str, factory, *, ttl=None):
        if key in stored:
            return stored[key]
        value = factory()
        stored[key] = value
        return value

    cache.get_or_set.side_effect = _get_or_set

    svc = MarketApplicationService(
        market_provider=provider,
        industry_provider=MagicMock(),
        stock_cache=None,
        cache=cache,
    )
    first = svc.get_panorama(MarketCode.CN)
    second = svc.get_panorama(MarketCode.CN)

    assert first.market_status == "open"
    assert second.sentiment_score == pytest.approx(55.0)
    assert provider.get_market_rankings.call_count == 1
