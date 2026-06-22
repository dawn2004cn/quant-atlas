from app.core.route_registry import _route_registry
market_routes = {k: v for k, v in _route_registry.items() if v.get('context') == 'market_data'}
print(f'Market data routes: {len(market_routes)}')
for name, info in sorted(market_routes.items()):
    fn = info.get('function', 'unknown')
    print(f'  {name}: {fn}')
