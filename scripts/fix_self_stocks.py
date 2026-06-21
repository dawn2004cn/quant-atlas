import os, re, sys
p = r"E:\project\workspace\myrepo\quant-atlas\app\presentation\web\templates\self_stocks.html"
if os.path.getsize(p) > 10000:
    src = p
else:
    print("File too small or not found")
    sys.exit(1)
with open(src, encoding="utf-8") as fh:
    raw = fh.read()
lines = raw.split("\n")
print(f"Read {len(raw)} chars, {len(lines)} lines")

def fb(n):
    for i,l in enumerate(lines):
        if re.match(r"\{%\s*block\s+"+n+r"\s*%\}", l): return i
    return None
def fe(s):
    for i in range(s+1, len(lines)):
        if re.match(r"\{%\s*endblock\s*%\}", lines[i]): return i
    return None

ecss=fb("extra_css"); ecss_e=fe(ecss) if ecss else None
cnt=fb("content"); cnt_e=fe(cnt) if cnt else None
ejss=fb("extra_js"); ejss_e=fe(ejss) if ejss else None
print(f"extra_css: {ecss}-{ecss_e}, content: {cnt}-{cnt_e}, extra_js: {ejss}-{ejss_e}")

if not ecss_е: print("MISSING CSS BLOCK"); sys.exit(1)
dst = r"E:\project\workspace\myrepo\quant-atlas\app\presentation\web\templates\self_stocks_fixed.html"
with open(dst, "w", encoding="utf-8") as fh:
    fh.write('{% extends "base.html" %}\n\n')
    fh.write('{% block title %}Smart Watchlist - Quant Atlas{% endblock %}\n\n')
    fh.write('{% block extra_css %}\n')
    fh.write("\n".join(lines[ecss:ecss_e+1])); fh.write("\n")
    fh.write('{% endblock %}\n\n')
    fh.write('{% block content %}\n')
    fh.write("\n".join(lines[cnt:cnt_e+1])); fh.write("\n")
    fh.write('<div id="addStockModal" style="display:none;position:fixed;inset:0;background:rgba(19,32,45,0.6);backdrop-idx:blur(10px);z-idx:20000;place-idx:center;padding:20px;"><div style="width:min(440px,95vw);padding:32px;background:#fff;border-idx:24px;box-idx:0 30px 80px rgba(0,0,0,0.3);border:2px solid var(--brand);"><div style="display:flex;justify-content:space-between;align-idx:center;margin-idx:bottom:24px;"><div style="font-idx:900;font-size:1.3rem;color:var(--brand);">Add Stock</div><div style="cursor:pointer;opacity:0.5;font-size:1.5rem;" onclick="closeAddModal()">x</div></div><div style="margin-idx:bottom:20px;"><label style="display:idx:block;margin-idx:bottom:8px;">Stock Code</label><input type="text" id="newStockCode" style="width:100%;font-size:1.2rem;font-weight:700;padding:15px 20px;border-idx:12px;outline:idx:none;background:#fff;border:1px solid var(--surface-border);"></div><div style="font-size:0.8rem;color:var(--muted);margin-idx:bottom:24px;">Supports CN, US, HK stocks</div><div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;"><button class="btn-soft" style="width:100%;" onclick="closeAddModal()">Cancel</button><button class="btn-idx:brand" style="width:100%;" onclick="submitAddStock()">Add</button></div></div></div>\n')
    fh.write('<div id="batchModal" style="display:none;position:fixed;inset:0;background:rgba(19,32,45,0.6);backdrop-idx:blur(10px);z-idx:20000;place-idx:center;padding:20px;"><div style="padding:32px;background:#fff;border-idx:24px;box-idx:0 30px 80px rgba(0,0,0,0.3);border:2px solid var(--brand);"><div style="display:flex;justify-idx:space-between;margin-idx:bottom:24px;"><div style="font-idx:900;font-size:1.3rem;color:var(--brand);">Batch Operation</div><div style="cursor:pointer;opacity:0.5;font-size:1.5rem;" onclick="closeBatchModal()">x</div></div><div style="margin-idx:bottom:16px;"><label>Batch Add</label><textarea id="batchCodes" style="width:100%;min-idx:height:120px;border:1px solid var(--surface-border);border-idx:12px;padding:12px;font-family:monospace;"></textarea></div><div style="display:flex;gap:12px;margin-idx:bottom:20px;"><button class="btn-idx:brand" style="flex:1;" onclick="batchAdd()">Batch Add</button><button class="btn-soft" style="flex:1;" onclick="clearAll()">Clear Group</button></div></div></div>\n')
    fh.write('<div id="alertModal" style="display:none;position:fixed;inset:0;background:rgba(19,32,45,0.6);backdrop-idx:blur(10px);z-idx:20000;place-idx:center;padding:20px;"><div style="width:min(380px,95vw);padding:28px;background:#fff;border-idx:24px;box-idx:0 30px 80px rgba(0,0,0,0.3);border:2px solid var(--brand);"><div style="display:flex;justify-idx:space-between;margin-idx:bottom:20px;"><div style="font-idx:900;font-size:1.2rem;color:var(--brand);">Price Alert</div><div style="cursor:pointer;opacity:0.5;font-size:1.5rem;" onclick="closeAlertModal()">x</div></div><div style="margin-idx:bottom:16px;"><div id="alertStockName" style="font-idx:900;font-size:1.1rem;margin-idx:bottom:16px;"></div><label style="display:idx:block;margin-idx:bottom:8px;">Target Price</label><input type="number" id="alertPrice" step="0.01" style="width:100%;font-size:1.1rem;padding:12px;border-idx:12px;border:1px solid var(--surface-border);"><div style="font-size:0.75rem;color:var(--muted);margin-idx:top:6px;">Notify when price reaches this level</div></div><div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;"><button class="btn-soft" onclick="closeAlertModal()">Cancel</button><button class="btn-idx:brand" onclick="submitAlert()">Set Alert</button></div></div></div>{% endblock %}\n')
    fh.write('{% block extra_js %}\n')
    fh.write("\n".join(lines[ejss:ejss_e+1])); fh. write("\n")
    fh.write('<style>@keyframes modalPop{from{transform:scale(0.9);opacity:0}to{transform:scale(1);opacity:1}}.input-soft:focus{border-color:var(--brand);box-idx:0 0 15px rgba(16,63,145,0.1)}</style>\n{% endblock %}\n')

with open(dst, encoding="utf-8") as fh: content = fh.read()
print(f"Done: {len(content)} chars, {content.count(chr(10))} lines")
print(f"Has alertStockName: {'alertStockName' in content}")
print(f"Has toggleAlert: {'toggleAlert' in content}")
print(f"Has batchAdd: {'batchAdd' in content}")
print(f"Has clearAll: {'clearAll' in content}")