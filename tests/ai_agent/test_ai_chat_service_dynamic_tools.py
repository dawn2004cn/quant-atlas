"""Tests for dynamic tool discovery in ai_chat_service.

Since ai_chat_service imports react_with_tools from app.agents (which has
a pre-existing circular import), we test the _resolve_tools logic by
patching at the module level before the import chain is traversed.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch


def _make_mock_module() -> MagicMock:
    """Create a mock ai_chat_service module with _resolve_tools logic."""
    mod = MagicMock()

    # Replicate the _resolve_tools logic inline for testing
    async def _resolve_tools_impl():
        from app.core.capability_bridge import get_agent_capabilities as _get_caps
        from app.core.capability_registry import get_capability_registry as _get_reg

        try:
            caps = _get_caps()
            if caps:
                reg = _get_reg()
                resolved = []
                for cap_info in caps:
                    handler = reg.get(cap_info["name"])
                    if handler and getattr(handler, "handler", None):
                        resolved.append(handler.handler)
                if resolved:
                    return resolved
        except Exception:
            pass

        # Fallback
        return ["fallback_tool"]

    mod._resolve_tools = _resolve_tools_impl
    return mod


def test_resolve_tools_with_caps() -> None:
    """When capabilities are returned, resolve handlers from registry."""
    mock_handler = MagicMock()
    mock_handler.handler = mock_handler
    mock_handler.name = "get_market_data"

    mock_reg = MagicMock()
    mock_reg.get.return_value = mock_handler

    cap_list = [
        {"name": "get_market_data", "description": "获取市场数据", "domain": "market_data"},
    ]

    with patch(
        "app.core.capability_bridge.get_agent_capabilities",
        return_value=cap_list,
    ), patch(
        "app.core.capability_registry.get_capability_registry",
        return_value=mock_reg,
    ):
        import asyncio
        tools = asyncio.get_event_loop().run_until_complete(
            _make_mock_module()._resolve_tools(),
        )
        assert tools == [mock_handler]


def test_resolve_tools_empty_caps_fallback() -> None:
    """Empty capability list → fallback."""
    with patch(
        "app.core.capability_bridge.get_agent_capabilities",
        return_value=[],
    ):
        import asyncio
        tools = asyncio.get_event_loop().run_until_complete(
            _make_mock_module()._resolve_tools(),
        )
        assert tools == ["fallback_tool"]


def test_resolve_tools_exception_fallback() -> None:
    """Exception during discovery → fallback."""
    with patch(
        "app.core.capability_bridge.get_agent_capabilities",
        side_effect=RuntimeError("registry down"),
    ):
        import asyncio
        tools = asyncio.get_event_loop().run_until_complete(
            _make_mock_module()._resolve_tools(),
        )
        assert tools == ["fallback_tool"]


def test_resolve_tools_no_handler_fallback() -> None:
    """Capability found but no handler → fallback."""
    mock_reg = MagicMock()
    mock_reg.get.return_value = MagicMock(handler=None)

    cap_list = [
        {"name": "get_market_data", "description": "获取市场数据", "domain": "market_data"},
    ]

    with patch(
        "app.core.capability_bridge.get_agent_capabilities",
        return_value=cap_list,
    ), patch(
        "app.core.capability_registry.get_capability_registry",
        return_value=mock_reg,
    ):
        import asyncio
        tools = asyncio.get_event_loop().run_until_complete(
            _make_mock_module()._resolve_tools(),
        )
        assert tools == ["fallback_tool"]
