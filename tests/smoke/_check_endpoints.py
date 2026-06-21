"""Check key API endpoints after refactoring."""
from app import create_app

app = create_app()
with app.app_context():
    print("Checking key endpoints that were 404 before:\n")
    key_routes = [
        '/api/v1/global/quote',
        '/api/v1/global/history',
        '/api/v1/markets/CN/quotes',
        '/api/v1/system/task-messages',
        '/api/v1/quotes',
    ]
    found = {}
    for rule in app.url_map.iter_rules():
        path = rule.rule
        methods = sorted(m for m in (rule.methods - {'HEAD', 'OPTIONS'}) if m)
        for k in key_routes:
            if k in path:
                found[k] = f"{methods} {path}"
                break
    for k, v in found.items():
        print(f"{v}")
        print(f"  -> {k} : FOUND")
    print(f"\nTotal key routes found: {len(found)}/{len(key_routes)}")
