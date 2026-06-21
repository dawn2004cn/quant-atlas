"""WebSocket adapter and THS session unit tests."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import requests

from app.infrastructure.providers.cn_ths_sectors import get_ths_session_from_settings
from app.infrastructure.realtime import websocket_adapter as ws


def test_broadcast_quote_update_targets_market_room():
    emitted: list[tuple[str, str, dict]] = []

    def _capture(room: str, event: str, data: dict) -> int:
        emitted.append((room, event, data))
        return 1

    with patch.object(ws, "broadcast_to_room", side_effect=_capture):
        n = ws.broadcast_quote_update("600519", 1500.0, 10.0, 0.67, 1000)

    assert n == 1
    assert emitted[0][0] == "market"
    assert emitted[0][1] == "quote_update"
    assert emitted[0][2]["symbol"] == "600519"


def test_get_ths_session_from_settings_without_credentials():
    settings = MagicMock()
    settings.ths.has_credentials = False

    with patch("app.config.get_settings", return_value=settings):
        session = get_ths_session_from_settings()

    assert isinstance(session, requests.Session)


def test_get_ths_session_from_settings_uses_credentials():
    settings = MagicMock()
    settings.ths.has_credentials = True
    settings.ths.username = "demo_user"
    settings.ths.password = "secret"
    mock_session = requests.Session()

    with (
        patch("app.config.get_settings", return_value=settings),
        patch(
            "app.infrastructure.providers.cn_ths_sectors.get_ths_session",
            return_value=mock_session,
        ) as get_sess,
    ):
        session = get_ths_session_from_settings()

    get_sess.assert_called_once_with("demo_user", "secret")
    assert session is mock_session


def test_hot_sector_init_ths_session_via_port():
    from app.modules.market_data.services.hot_sector_service import HotSectorService

    port = MagicMock()
    port.get_ths_session_from_settings.return_value = requests.Session()

    with patch(
        "app.modules.market_data.services.hot_sector_service.get_cn_sector_board_port",
        return_value=port,
    ):
        svc = HotSectorService(cache_ttl_sec=1)

    port.get_ths_session_from_settings.assert_called()
    assert svc._ths_session is not None
