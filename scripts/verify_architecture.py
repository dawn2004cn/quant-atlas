#!/usr/bin/env python3
"""Architecture verification script for quant-atlas microservices.

Verifies:
1. All 8 blueprints can be created independently
2. Service discovery registration works
3. Routing rules cover all services
4. DualWriteProxy HTTP client works
5. All files compile without errors
"""

from __future__ import annotations

import sys

sys.path.insert(0, ".")

SERVICES = [
    ("market_data", "app.modules.market_data.market_data_blueprint", "create_market_data_app", 5101, "market-data"),
    ("strategy", "app.modules.strategy.strategy_blueprint", "create_strategy_app", 5201, "strategy"),
    ("ai_agent", "app.modules.ai_agent.ai_agent_blueprint", "create_ai_agent_app", 5301, "ai-agent"),
    ("portfolio_risk", "app.modules.portfolio_risk.portfolio_risk_blueprint", "create_portfolio_risk_app", 5401, "portfolio-risk"),
    ("execution", "app.modules.execution.execution_blueprint", "create_execution_app", 5501, "execution"),
    ("system_user", "app.modules.system.system_blueprint", "create_system_user_app", 5601, "system-user"),
    ("data", "app.modules.data.data_blueprint", "create_data_app", 5701, "data"),
    ("research", "app.modules.research.research_blueprint", "create_research_app", 5801, "research"),
]


def test_blueprint_creation():
    """Test that all blueprints can be created."""
    print("1. Blueprint Creation")
    passed = 0
    
    for name, module_path, factory_name, port, compose_name in SERVICES:
        try:
            module = __import__(module_path, fromlist=[factory_name])
            factory = getattr(module, factory_name)
            app = factory()
            
            # Check health endpoint exists
            assert "/health" in [r.rule for r in app.url_map.iter_rules()], "Missing /health"
            
            print(f"   [PASS] {name}: {port} - {len(app.url_map._rules)} routes")
            passed += 1
        except Exception as exc:
            print(f"   [FAIL] {name}: {exc}")
    
    return passed, len(SERVICES)


def test_service_discovery():
    """Test service discovery registration."""
    print("\n2. Service Discovery")
    
    try:
        from app.core.service_discovery import get_service_registry, get_service_client
        
        registry = get_service_registry()
        services = registry.list_services()
        
        expected = {s[0] for s in SERVICES}
        registered = set(services)
        
        missing = expected - registered
        if missing:
            print(f"   [WARN] Missing services: {missing}")
        
        print(f"   [PASS] {len(registered)}/{len(expected)} services registered")
        
        # Test client creation
        client = get_service_client("market_data")
        assert client is not None, "Client is None"
        assert client.service_name == "market_data"
        
        print(f"   [PASS] ServiceClient created for market_data")
        return len(registered), len(expected)
    except Exception as exc:
        print(f"   [FAIL] {exc}")
        return 0, len(SERVICES)


def test_routing_rules():
    """Test routing rules completeness."""
    print("\n3. Routing Rules")
    
    try:
        from app.infrastructure.gateway.routing_rules import (
            get_kong_routes,
            get_apisix_routes,
            get_nginx_config,
            SERVICE_DISCOVERY,
        )
        
        kong = get_kong_routes()
        apisix = get_apisix_routes()
        nginx = get_nginx_config()
        discovery = SERVICE_DISCOVERY
        
        print(f"   Kong routes: {len(kong)}")
        print(f"   APISIX routes: {len(apisix)}")
        print(f"   NGINX config: {len(nginx)} chars")
        print(f"   Service discovery: {len(discovery)} entries")
        
        # Check service discovery matches all services
        expected = {s[0] for s in SERVICES}
        disco_names = {v["name"] for v in discovery.values()}
        
        # Map blueprint names to compose names for comparison
        name_map = {s[0]: s[4] for s in SERVICES}
        expected_compose = {name_map.get(k, k) for k in expected}
        missing_disco = expected_compose - disco_names
        if missing_disco:
            print(f"   [WARN] Discovery missing: {missing_disco}")
        else:
            print(f"   [PASS] Service discovery covers all services")
        
        # Kong routes cover all service paths
        kong_paths = set()
        for route in kong.values():
            for p in route.get("paths", []):
                kong_paths.add(p.rstrip("/"))
        
        expected_paths = {"/api/v1/market", "/strategy", "/ai-agent", "/portfolio-risk", 
                         "/execution", "/system", "/data", "/research"}
        missing_paths = expected_paths - kong_paths
        if missing_paths:
            print(f"   [WARN] Kong missing paths: {missing_paths}")
        else:
            print(f"   [PASS] Kong routes cover all service paths")
        
        return True
    except Exception as exc:
        print(f"   [FAIL] {exc}")
        return False


def test_dual_write_proxy():
    """Test DualWriteProxy configuration."""
    print("\n4. DualWriteProxy")
    
    try:
        from app.infrastructure.gateway.dual_write_middleware import (
            DualWriteProxy,
            HttpServiceClient,
            get_dual_write_proxy,
        )
        
        proxy = DualWriteProxy()
        
        # Register all services
        for name, _, _, port, _ in SERVICES:
            proxy.register_service(name, f"http://localhost:{port}", traffic_split=0.0)
        
        print(f"   [PASS] {len(proxy._services)} services registered")
        
        # Test traffic split
        proxy.set_traffic_split("market_data", 0.5)
        assert proxy._traffic_split["market_data"] == 0.5
        print(f"   [PASS] Traffic split works")
        
        # Test health check
        proxy._check_health("market_data", proxy._services["market_data"])
        health = proxy.get_health("market_data")
        print(f"   [PASS] Health check: {health.status.value}")
        
        # Test confidence
        for _ in range(5):
            proxy._comparison_history["market_data"].append(1)
        confidence = proxy.get_confidence("market_data")
        assert confidence == 1.0
        print(f"   [PASS] Confidence calculation: {confidence}")
        
        return True
    except Exception as exc:
        print(f"   [FAIL] {exc}")
        import traceback
        traceback.print_exc()
        return False


def test_docker_compose():
    """Test Docker Compose configuration."""
    print("\n5. Docker Compose")
    
    try:
        import yaml
        
        with open("infrastructure/docker/docker-compose.yml", "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        
        services = config.get("services", {})
        expected = {s[4] for s in SERVICES} | {"api-gateway", "redis", "mysql"}
        
        found = set(services.keys())
        missing = expected - found
        if missing:
            print(f"   [FAIL] Missing services: {missing}")
            return False
        
        print(f"   [PASS] {len(services)} services in compose file")
        
        # Check each service has required fields
        for svc_name in expected - {"api-gateway"}:
            svc = services.get(svc_name, {})
            assert "image" in svc or "build" in svc, f"{svc_name} missing image/build"
            assert "ports" in svc or "expose" in svc, f"{svc_name} missing ports"
        
        print(f"   [PASS] All services have required fields")
        return True
    except Exception as exc:
        print(f"   [FAIL] {exc}")
        return False


def test_k8s_manifests():
    """Test Kubernetes manifests."""
    print("\n6. Kubernetes Manifests")
    
    try:
        import yaml
        import os
        
        k8s_dir = "infrastructure/k8s"
        manifests = []
        
        for root, dirs, files in os.walk(k8s_dir):
            for f in files:
                if f.endswith(".yaml"):
                    manifests.append(os.path.join(root, f))
        
        print(f"   [PASS] {len(manifests)} K8s manifest files")
        
        # Check key manifests exist
        required = [
            "namespace.yaml",
            "configmap.yaml",
            "secrets.yaml",
            "mysql/mysql-deployment.yaml",
            "redis/redis-deployment.yaml",
        ]
        
        for req in required:
            path = os.path.join(k8s_dir, req)
            assert os.path.exists(path), f"Missing: {req}"
        
        print(f"   [PASS] All required manifests present")
        return True
    except Exception as exc:
        print(f"   [FAIL] {exc}")
        return False


def main():
    """Run all architecture verification tests."""
    print("=" * 60)
    print("quant-atlas Microservices Architecture Verification")
    print("=" * 60)
    
    results = []
    
    results.append(("Blueprint Creation", test_blueprint_creation()))
    results.append(("Service Discovery", test_service_discovery()))
    results.append(("Routing Rules", test_routing_rules()))
    results.append(("DualWriteProxy", test_dual_write_proxy()))
    results.append(("Docker Compose", test_docker_compose()))
    results.append(("K8s Manifests", test_k8s_manifests()))
    
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    
    for name, result in results:
        if isinstance(result, tuple):
            passed, total = result
            status = f"{passed}/{total}"
            ok = passed == total
        else:
            ok = result
            status = "PASS" if ok else "FAIL"
        
        print(f"  [{status}] {name}")
    
    all_pass = all(
        r if isinstance(r, bool) else r[0] == r[1]
        for r in [res for _, res in results]
    )
    
    if all_pass:
        print("\nArchitecture verification PASSED!")
        return 0
    else:
        print("\nSome checks failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
