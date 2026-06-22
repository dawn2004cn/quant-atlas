import os, sys
sys.stdout.reconfigure(encoding="utf-8")
templates_dir = "E:/project/workspace/myrepo/quant-atlas/app/presentation/web/templates"

def hybrid_decode(raw):
    result = bytearray()
    i = 0
    while i < len(raw):
        b = raw[i]
        if b < 0x80:
            result.append(b); i += 1
        elif b >= 0xC0 and b < 0xF8:
            if b >= 0xF0: seq_len = 4
            elif b >= 0xE0: seq_len = 3
            else: seq_len = 2
            if i + seq_len <= len(raw):
                seq = raw[i:i+seq_len]
                try: seq.decode("utf-8"); result.extend(seq); i += seq_len; continue
                except: pass
            if i + 1 < len(raw):
                pair = raw[i:i+2]
                try: decoded = pair.decode("gbk"); result.extend(decoded.encode("utf-8")); i += 2; continue
                except: pass
            result.append(ord("?")); i += 1
        else:
            if i + 1 < len(raw):
                pair = raw[i:i+2]
                try: decoded = pair.decode("gbk"); result.extend(decoded.encode("utf-8")); i += 2; continue
                except: pass
            result.append(ord("?")); i += 1
    return result.decode("utf-8")

for root, dirs, files in os.walk(templates_dir):
    for f in files:
        if not f.endswith(".html"):
            continue
        path = os.path.join(root, f)
        raw = open(path, "rb").read()
        try:
            raw.decode("utf-8")
        except UnicodeDecodeError:
            text = hybrid_decode(raw)
            # Output as base64 so it can be safely piped back
            import base64
            encoded = base64.b64encode(text.encode("utf-8")).decode("ascii")
            rel = os.path.relpath(path, templates_dir).replace("\\", "/")
            print("FILE:" + rel)
            print(encoded)
