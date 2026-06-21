"""Check all API endpoints."""
from app import create_app

app = create_app()
with app.app_context():
    routes = []
    for rule in app.url_map.iter_rules():
        if rule.endpoint != 'static':
            methods = rule.methods - {'HEAD', 'OPTIONS'}
            routes.append(f'{methods} {rule.rule}')
    print(f'Total routes: {len(routes)}')
    for r in sorted(routes):
        print(r)
