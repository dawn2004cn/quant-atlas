import re, py_compile

PATH = "E:\\project\\workspace\\myrepo\\quant-atlas\\app\\modules\\system\\services\\institution_tier_service.py"

with open(PATH, "r", encoding="utf-8") as f:
    lines = f.readlines()

re_def = re.compile(r"^    def \w+")
re_class = re.compile(r"^class \w+")

# Fix 1: Remove duplicated _load_nodes_map
for i, l in enumerate(lines):
    if l.count(" ") >= 5 and l.count("    ") == 5 and "def _load_nodes_map" in l:
        lines[i] = None
        print(f"Fix 1: Removed line {i+1}")

# Fix 2: Merge split fh.write line
for i, l in enumerate(lines):
    if l is not None and "fh.write(json.dumps(record" in l:
        if i+1 < len(lines) and lines[i+1] is not None and lines[i+1].strip() == "\x22\x29":
            lines[i] = '            fh.write(json.dumps(record, ensure_ascii=False) + "\\n")\n'
            lines[i+1] = None
            print(f"Fix 2: Merged lines {i+1} and {i+2}")

# Fix 3: Remove second duplicate import_model (after register_node)
register_idx = None
import_first = None
import_second = None
for i, l in enumerate(lines):
    if l is not None and "def register_node" in l:
        register_idx = i
    if l is not None and "def import_model" in l:
        if import_first is None:
            import_first = i
        else:
            import_second = i

print(f"import_1 at L{import_first+1}, register at L{register_idx+1}, import_2 at L{import_second+1}")

if import_second and import_second > register_idx:
    start = import_second
    end = start + 1
    while end < len(lines):
        if lines[end] is not None and (re_def.match(lines[end]) or re_class.match(lines[end])):
            break
        end += 1
    for j in range(start, end):
        lines[j] = None
    print(f"Fix 3: Removed L{start+1}-L{end}")

# Remove None lines
lines = [l for l in lines if l is not None]

# Condense blank lines
result = []
blank = 0
for l in lines:
    if l.strip() == "":
        blank += 1
        if blank <= 2:
            result.append(l)
    else:
        blank = 0
        result.append(l)

with open(PATH, "w", encoding="utf-8") as f:
    f.writelines(result)

print(f"Written: {len(result)} lines")

py_compile.compile(PATH, doraise=True)
print("Compiles OK!")

import ast
with open(PATH, "r", encoding="utf-8") as f:
    tree = ast.parse(f.read())
for n in ast.walk(tree):
    if isinstance(n, ast.ClassDef):
        methods = [x.name for x in n.body if isinstance(x, (ast.FunctionDef, ast.AsyncFunctionDef))]
        dupes = {m for m in methods if methods.count(m) > 1}
        label = f" [DUPLICATES: {dupes}]" if dupes else ""
        print(f"  {n.name}: {methods}{label}")
