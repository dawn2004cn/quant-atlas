"""Verify Phase 15-17 endpoints via Playwright (handles login)."""
import sys
from playwright.sync_api import sync_playwright

BASE = "http://localhost:5000"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context()
    page = context.new_page()
    results = []

    # Login
    page.goto(f"{BASE}/login", wait_until="networkidle", timeout=15000)
    page.fill("#username", "admin")
    page.fill("#password", "admin")
    page.click("button[type=submit]")
    page.wait_for_load_state("networkidle")
    print("  LOGIN OK")

    def api(url, method="GET", body=None):
        opts = f"method:'{method}'"
        if body:
            import json
            opts += f",headers:{{'Content-Type':'application/json'}},body:JSON.stringify({json.dumps(body)})"
        return page.evaluate(f"""(async () => {{
            const r = await fetch('{url}', {{{opts}}});
            const t = await r.text();
            let j; try {{ j = JSON.parse(t); }} catch(e) {{ j = null; }}
            return {{ok: r.ok, status: r.status, json: j}};
        }})()""")

    # 1. Health
    r = api("/api/v1/system/health")
    results.append(("PASS" if r["ok"] and r["json"] else "FAIL", f"GET /system/health -> {r['status']}"))

    # 2. Truth badge
    r = api("/api/v1/truth/badge/CN/600519")
    data = (r["json"] or {}).get("data", {})
    results.append(("PASS" if r["ok"] else "FAIL", f"GET /truth/badge/CN/600519 -> {r['status']}"))
    results.append(("PASS" if "confidence" in data else "FAIL", f"  confidence={data.get('confidence', '?')}"))

    # 3. Data verify
    r = api("/api/v1/data/verify/CN/600519")
    results.append(("PASS" if r["ok"] else "FAIL", f"GET /data/verify/CN/600519 -> {r['status']}"))

    # 4. Wallet credit
    r = api("/api/v1/alpha/wallet/credit", "POST", {"user_id": 1, "amount": 100})
    bal = (r["json"] or {}).get("data", {}).get("balance") if r["json"] else None
    results.append(("PASS" if r["ok"] else "FAIL", f"POST /alpha/wallet/credit -> {r['status']} balance={bal}"))

    # 5. Wallet balance
    r = api("/api/v1/alpha/wallet/balance?user_id=1")
    bal2 = (r["json"] or {}).get("data", {}).get("balance") if r["json"] else None
    results.append(("PASS" if r["ok"] else "FAIL", f"GET /alpha/wallet/balance -> {r['status']} balance={bal2}"))

    # 6. Listings
    r = api("/api/v1/alpha/marketplace/listings?active=true")
    items = (r["json"] or {}).get("data", []) if r["json"] else []
    results.append(("PASS" if r["ok"] else "FAIL", f"GET /alpha/marketplace/listings -> {r['status']} ({len(items)} items)"))

    # 7. Orders
    r = api("/api/v1/alpha/marketplace/orders?buyer_id=1")
    orders = (r["json"] or {}).get("data", {}).get("orders", []) if r["json"] else []
    results.append(("PASS" if r["ok"] else "FAIL", f"GET /alpha/marketplace/orders -> {r['status']} ({len(orders)} orders)"))

    # 8. Marketplace page
    page.goto(f"{BASE}/alpha-marketplace", wait_until="networkidle", timeout=15000)
    title = page.title()
    results.append(("PASS" if "marketplace" in title.lower() or "alpha" in title.lower() else "FAIL", f"GET /alpha-marketplace -> title='{title}'"))

    # Summary
    passed = sum(1 for s, _ in results if s == "PASS")
    total = len(results)
    print(f"\n{'='*40}")
    for status, msg in results:
        print(f"  {status}: {msg}")
    print(f"\nResults: {passed}/{total} passed")
    if passed < total:
        sys.exit(1)
    else:
        print("ALL CHECKS PASSED")

    browser.close()