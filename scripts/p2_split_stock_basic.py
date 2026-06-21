import re
import py_compile

with open("app/presentation/api/v1/stock/stock_basic.py", encoding="utf-8") as f:
    lines = f.readlines()

# Find route boundaries
starts = [i for i, l in enumerate(lines) if "@blueprint.get(" in l]
starts.append(len(lines))

names = {
    0: ("stock_search", "register_stock_search", "Stock search", "search"),
    1: ("stock_quote", "register_stock_quote", "Stock quotes", "quote"),
    2: ("stock_detail", "register_stock_detail", "Stock detail", "detail"),
    3: ("stock_history", "register_stock_history", "Stock history Kline", "history"),
}

HEADER = """from __future__ import annotations
from flask import Blueprint
from flask_login import login_required
from app.core.registry import register_routes
from ...v1_context import ApiV1Context
from ...common import ok_response
from ...decorators import service_fallback
from ...dto_validation import validate_request
from .....application.dto.request_dtos import StockSearchRequestDTO, QuoteRequestDTO
from .....application.dto.market_data_dto import StockHistoryDTO as StockHistoryRequest
StockSearchRequest = StockSearchRequestDTO
StockQuoteRequest = QuoteRequestDTO
"""

for idx, (route_s, route_e) in enumerate(zip(starts[:-1], starts[1:])):
    rname, fname, desc, fname_suffix = names[idx]
    
    body_lines = lines[route_s:route_e]
    body_lines = [l[4:] if l.startswith("    ") else l for l in body_lines]
    body = "".join(body_lines).rstrip() + "\n"
    
    out_path = "app/presentation/api/v1/stock/routes_%s.py" % fname_suffix
    
    fn_line = '@register_routes(name="%s", context="market_data", description="%s")\ndef %s(blueprint: Blueprint, ctx: ApiV1Context) -> None:\n    legacy = ctx.enable_legacy_response_fields\n\n' % (rname, desc, fname)
    
    full = HEADER + "\n" + fn_line + body
    
    with open(out_path, "w", encoding="utf-8") as fs:
        fs.write(full)
    print("Created: %s" % out_path)
    
    try:
        py_compile.compile(out_path, doraise=True)
        print("  OK: %s" % out_path)
    except py_compile.PyCompileError as e:
        print("  FAIL: %s: %s" % (out_path, str(e)[:120]))

# Create shim
shim = 'from .routes_search import *\nfrom .routes_quote import *\nfrom .routes_detail import *\nfrom .routes_history import *\n'
with open("app/presentation/api/v1/stock/stock_basic.py", "w", encoding="utf-8") as f:
    f.write(shim)
try:
    py_compile.compile("app/presentation/api/v1/stock/stock_basic.py", doraise=True)
    print("OK: stock_basic.py (shim)")
except py_compile.PyCompileError as e:
    print("FAIL: stock_basic.py: %s" % str(e)[:120])

print("\nDone.")