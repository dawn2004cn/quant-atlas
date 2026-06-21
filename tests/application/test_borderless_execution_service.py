from __future__ import annotations

from app.modules.execution.services.borderless_execution_service import BorderlessExecutionService
from app.domain.execution.market_router import infer_market, resolve_execution_route
from app.infrastructure.execution.borderless_router import BorderlessExecutionRouter
from app.infrastructure.execution.drivers.paper_driver import PaperExecutionDriver


def test_infer_market_covers_multi_markets() -> None:
    assert infer_market("600519").value == "CN"
    assert infer_market("AAPL").value == "US"
    assert infer_market("0700.HK").value == "HK"
    assert infer_market("BTCUSDT").value == "CRYPTO"
    assert infer_market("sz000001", "CN").value == "CN"


def test_resolve_route_picks_paper_driver() -> None:
    route = resolve_execution_route("AAPL", mode="paper")
    assert route.market.value == "US"
    assert route.driver_id == "paper_us"


def test_borderless_submit_order_fills_paper() -> None:
    router = BorderlessExecutionRouter(default_mode="paper")
    for market in ("CN", "US", "HK", "CRYPTO"):
        router.register_driver(
            f"paper_{market.lower()}",
            PaperExecutionDriver(market=market),
        )
    svc = BorderlessExecutionService(router=router)
    out = svc.submit_order(
        {
            "symbol": "600519",
            "market": "CN",
            "side": "buy",
            "order_type": "market",
            "quantity": 100,
            "price": 1800.0,
            "provenance_id": "prov_test_001",
        }
    )
    assert out["ok"] is True
    assert out["route"]["market"] == "CN"
    assert out["response"]["status"] == "filled"
    assert out["provenance_id"] == "prov_test_001"


def test_execution_manifest_lists_drivers() -> None:
    svc = BorderlessExecutionService()
    manifest = svc.get_manifest()
    assert manifest["ok"] is True
    assert "CN" in manifest["markets"]
    assert len(manifest["drivers"]) >= 8
    driver_ids = {d["driver_id"] for d in manifest["drivers"]}
    assert "redis_crypto" in driver_ids
    assert "paper_us" in driver_ids


def test_crypto_order_uses_redis_driver_with_paper_fallback() -> None:
    from app.infrastructure.execution.driver_registry import build_borderless_router

    svc = BorderlessExecutionService(router=build_borderless_router(mode="paper"))
    out = svc.submit_order(
        {
            "symbol": "BTCUSDT",
            "side": "buy",
            "order_type": "market",
            "quantity": 0.01,
            "price": 65000.0,
            "provenance_id": "prov_crypto_001",
        }
    )
    assert out["ok"] is True
    assert out["route"]["market"] == "CRYPTO"
    assert out["route"]["driver_id"] == "redis_crypto"
    assert out["response"]["status"] == "filled"


def test_us_stock_order_fills_paper_driver() -> None:
    from app.infrastructure.execution.driver_registry import build_borderless_router

    svc = BorderlessExecutionService(router=build_borderless_router(mode="paper"))
    out = svc.submit_order(
        {
            "symbol": "AAPL",
            "market": "US",
            "side": "buy",
            "order_type": "market",
            "quantity": 10,
            "price": 190.0,
            "provenance_id": "prov_us_001",
        }
    )
    assert out["ok"] is True
    assert out["route"]["market"] == "US"
    assert out["route"]["driver_id"] == "paper_us"
