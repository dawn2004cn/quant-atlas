#!/usr/bin/env python3
"""Unit tests for DualWriteProxy HTTP client.

Uses unittest.mock to avoid network dependencies.
"""

from __future__ import annotations

import sys
import time
from unittest.mock import MagicMock, patch

sys.path.insert(0, ".")

from app.infrastructure.gateway.dual_write_middleware import (
    DualWriteProxy,
    HttpServiceClient,
    DualWriteConfig,
    ServiceStatus,
)


class TestHttpServiceClient:
    """Tests for HttpServiceClient."""
    
    def _make_mock_response(self, status=200, body='{"result": "ok"}', content_type="application/json"):
        mock_resp = MagicMock()
        mock_resp.status = status
        mock_resp.headers.get.return_value = content_type
        mock_resp.read.return_value = body.encode() if isinstance(body, str) else body
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        return mock_resp
    
    def test_call_get(self):
        """Test GET request."""
        client = HttpServiceClient("http://test:5000", timeout=5.0)
        
        mock_response = self._make_mock_response(body='{"result": "ok"}')
        
        with patch("urllib.request.urlopen", return_value=mock_response):
            result = client.call("GET", "/get", params={"test": "value"})
        
        assert result == {"result": "ok"}, f"Expected dict, got {result}"
    
    def test_call_post_json_body(self):
        """Test POST with JSON body."""
        client = HttpServiceClient("http://test:5000", timeout=5.0)
        
        mock_response = self._make_mock_response(body='{"id": 123}')
        
        with patch("urllib.request.urlopen", return_value=mock_response):
            result = client.call("POST", "/post", body={"key": "value"})
        
        assert result == {"id": 123}
    
    def test_call_with_params(self):
        """Test request with query params."""
        client = HttpServiceClient("http://test:5000", timeout=5.0)
        
        mock_response = self._make_mock_response(body='{"ok": true}')
        
        with patch("urllib.request.urlopen", return_value=mock_response):
            result = client.call("GET", "/get", params={"a": "1", "b": "2"})
        
        assert result == {"ok": True}
    
    def test_http_error(self):
        """Test HTTP error handling."""
        client = HttpServiceClient("http://test:5000", timeout=5.0)
        
        import urllib.error
        mock_error = MagicMock()
        mock_error.code = 404
        mock_error.read.return_value = b'{"error": "not found"}'
        mock_error.fp = MagicMock()
        
        with patch("urllib.request.urlopen", side_effect=urllib.error.HTTPError(
            "http://test:5000/test", 404, "Not Found", {}, mock_error
        )):
            try:
                client.call("GET", "/test")
                assert False, "Should have raised"
            except RuntimeError as exc:
                assert "404" in str(exc)


class TestDualWriteProxy:
    """Tests for DualWriteProxy."""
    
    def test_register_by_url(self):
        """Test registering service by URL string."""
        proxy = DualWriteProxy()
        proxy.register_service("test", "http://test:5000")
        
        assert "test" in proxy._services
        assert proxy._service_urls["test"] == "http://test:5000"
    
    def test_register_by_client(self):
        """Test registering service by client object."""
        proxy = DualWriteProxy()
        client = MagicMock()
        proxy.register_service("test", client)
        
        assert proxy._services["test"] == client
    
    def test_traffic_split(self):
        """Test traffic split configuration."""
        proxy = DualWriteProxy()
        proxy.register_service("test", "http://test:5000")
        
        proxy.set_traffic_split("test", 0.0)
        assert proxy._traffic_split["test"] == 0.0
        
        proxy.set_traffic_split("test", 1.0)
        assert proxy._traffic_split["test"] == 1.0
        
        proxy.set_traffic_split("test", 0.5)
        assert proxy._traffic_split["test"] == 0.5
        
        # Test clamping
        proxy.set_traffic_split("test", -0.5)
        assert proxy._traffic_split["test"] == 0.0
        
        proxy.set_traffic_split("test", 1.5)
        assert proxy._traffic_split["test"] == 1.0
    
    def test_health_check_success(self):
        """Test successful health check."""
        proxy = DualWriteProxy()
        proxy.register_service("test", "http://test:5000")
        
        client = proxy._services["test"]
        assert hasattr(client, 'base_url'), "Client should have base_url"
        
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.read.return_value = b'{"status": "healthy"}'
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        
        with patch("urllib.request.urlopen", return_value=mock_response):
            proxy._check_health("test", client)
        
        health = proxy.get_health("test")
        assert health.status == ServiceStatus.HEALTHY, f"Expected HEALTHY, got {health.status}"
        assert health.latency_ms >= 0, f"Expected latency >= 0, got {health.latency_ms}"
    
    def test_health_check_failure(self):
        """Test health check failure handling."""
        proxy = DualWriteProxy()
        proxy.register_service("test", "http://test:5000")
        
        client = proxy._services["test"]
        
        import urllib.error
        with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("connection refused")):
            for _ in range(4):
                proxy._check_health("test", client)
        
        health = proxy.get_health("test")
        assert health.status == ServiceStatus.DOWN
    
    def test_route_monolith(self):
        """Test routing to monolith when split is 0."""
        proxy = DualWriteProxy()
        proxy.register_service("test", "http://test:5000", traffic_split=0.0)
        
        mock_request = MagicMock()
        mock_request.method = "GET"
        mock_request.path = "/api/v1/test"
        mock_request.query_string = b""
        mock_request.headers = {}
        mock_request.data = b""
        
        mock_handler = MagicMock(return_value="monolith_response")
        
        # With split=0.0, should always route to monolith
        for _ in range(10):
            result = proxy.route("test", mock_request, mock_handler)
            assert result == "monolith_response"
            mock_handler.assert_called_once()
            mock_handler.reset_mock()
    
    def test_route_service(self):
        """Test routing to service when split is 1.0."""
        proxy = DualWriteProxy()
        proxy.register_service("test", "http://test:5000", traffic_split=1.0)
        
        mock_request = MagicMock()
        mock_request.method = "GET"
        mock_request.path = "/api/v1/test"
        mock_request.query_string = b""
        mock_request.headers = {}
        mock_request.data = b""
        
        mock_handler = MagicMock(return_value="monolith_response")
        
        client = proxy._services["test"]
        mock_response = {"data": "service_response"}
        
        with patch.object(client, "call", return_value=mock_response):
            result = proxy.route("test", mock_request, mock_handler)
        
        assert result == ("service_response", 200)
    
    def test_route_fallback_on_error(self):
        """Test fallback to monolith on service error."""
        proxy = DualWriteProxy()
        proxy.register_service("test", "http://test:5000", traffic_split=1.0)
        
        mock_request = MagicMock()
        mock_request.method = "GET"
        mock_request.path = "/api/v1/test"
        mock_request.query_string = b""
        mock_request.headers = {}
        mock_request.data = b""
        
        mock_handler = MagicMock(return_value="monolith_response")
        
        client = proxy._services["test"]
        
        with patch.object(client, "call", side_effect=RuntimeError("service down")):
            result = proxy.route("test", mock_request, mock_handler)
        
        assert result == "monolith_response"
        assert mock_handler.call_count == 1
    
    def test_confidence(self):
        """Test confidence calculation."""
        proxy = DualWriteProxy()
        proxy.register_service("test", "http://test:5000")
        
        # No comparisons yet
        assert proxy.get_confidence("test") == 0.0
        
        # Add 10 matches
        for _ in range(10):
            proxy._comparison_history["test"].append(1)
        
        assert proxy.get_confidence("test") == 1.0
        
        # Add some mismatches
        proxy._comparison_history["test"].append(0)
        proxy._comparison_history["test"].append(0)
        
        confidence = proxy.get_confidence("test")
        assert confidence == 10 / 12, f"Expected 0.833, got {confidence}"
    
    def test_should_cutover(self):
        """Test cutover readiness check."""
        proxy = DualWriteProxy()
        proxy.register_service("test", "http://test:5000")
        
        # Not ready without health data
        assert not proxy.should_cutover("test")
        
        # Set healthy state
        with proxy._lock:
            proxy._health["test"].status = ServiceStatus.HEALTHY
            proxy._health["test"].success_count = 100
            proxy._health["test"].error_count = 0
            proxy._health["test"].latency_ms = 100.0
        
        # Add confidence history
        for _ in range(20):
            proxy._comparison_history["test"].append(1)
        
        assert proxy.should_cutover("test")
    
    def test_response_normalization(self):
        """Test response normalization for comparison."""
        proxy = DualWriteProxy()
        
        resp1 = {
            "data": [1, 2, 3],
            "timestamp": "2024-01-01T00:00:00Z",
            "server_time": "2024-01-01T00:00:01Z",
            "latency_ms": 50,
        }
        
        resp2 = {
            "data": [1, 2, 3],
            "timestamp": "2024-01-01T00:00:05Z",  # Different timestamp
            "server_time": "2024-01-01T00:00:06Z",
            "latency_ms": 60,  # Different latency
        }
        
        norm1 = proxy._normalize(resp1)
        norm2 = proxy._normalize(resp2)
        
        # Timestamps and latency should be stripped
        assert "timestamp" not in norm1
        assert "server_time" not in norm1
        assert "latency_ms" not in norm1
        
        # Data should be the same
        assert norm1["data"] == norm2["data"]
        
        # Responses should match after normalization
        assert norm1 == norm2


def main():
    """Run all tests."""
    import traceback
    
    tests = [
        ("HttpServiceClient.call GET", lambda: TestHttpServiceClient().test_call_get()),
        ("HttpServiceClient.call POST JSON", lambda: TestHttpServiceClient().test_call_post_json_body()),
        ("HttpServiceClient.call params", lambda: TestHttpServiceClient().test_call_with_params()),
        ("HttpServiceClient HTTP error", lambda: TestHttpServiceClient().test_http_error()),
        ("DualWriteProxy register by URL", lambda: TestDualWriteProxy().test_register_by_url()),
        ("DualWriteProxy register by client", lambda: TestDualWriteProxy().test_register_by_client()),
        ("DualWriteProxy traffic split", lambda: TestDualWriteProxy().test_traffic_split()),
        ("DualWriteProxy health check success", lambda: TestDualWriteProxy().test_health_check_success()),
        ("DualWriteProxy health check failure", lambda: TestDualWriteProxy().test_health_check_failure()),
        ("DualWriteProxy route monolith", lambda: TestDualWriteProxy().test_route_monolith()),
        ("DualWriteProxy route service", lambda: TestDualWriteProxy().test_route_service()),
        ("DualWriteProxy route fallback", lambda: TestDualWriteProxy().test_route_fallback_on_error()),
        ("DualWriteProxy confidence", lambda: TestDualWriteProxy().test_confidence()),
        ("DualWriteProxy should cutover", lambda: TestDualWriteProxy().test_should_cutover()),
        ("DualWriteProxy normalize", lambda: TestDualWriteProxy().test_response_normalization()),
    ]
    
    print("=" * 60)
    print("DualWriteProxy Unit Tests")
    print("=" * 60)
    
    passed = 0
    failed = 0
    
    for name, test_func in tests:
        try:
            test_func()
            print(f"  [PASS] {name}")
            passed += 1
        except Exception as exc:
            print(f"  [FAIL] {name}: {exc}")
            failed += 1
            traceback.print_exc()
    
    print("\n" + "=" * 60)
    print(f"Results: {passed}/{passed + failed} passed")
    
    if failed > 0:
        print(f"Failed: {failed}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
