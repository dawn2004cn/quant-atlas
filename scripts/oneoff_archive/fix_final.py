"""Final fix for institution_tier_service.py - remove duplicate and split lines."""
import re

PATH = "E:\\project\\workspace\\myrepo\\quant-atlas\\app\\modules\\system\\services\\institution_tier_service.py"

with open(PATH, "r", encoding="utf-8") as f:
    content = f.read()

# Remove: duplicated '                def _load_nodes_map(self)...' that appears
# as a continuation of the for loop body
content = content.replace(
    '                    continue\n                    def _load_nodes_map(self) -> dict[str, DeploymentNode]:\n',
    '                    continue\n'
)

# Fix: split string literal across two lines
content = content.replace(
    'fh.write(json.dumps(record, ensure_ascii=False) + "\n"\n")\n',
    'fh.write(json.dumps(record, ensure_ascii=False) + "\\n")\n'
)

with open(PATH, "w", encoding="utf-8") as f:
    f.write(content)

import py_compile
py_compile.compile(PATH, doraise=True)
print("Compiles OK!")

# Verify structure
import ast
with open(PATH, "r", encoding="utf-8") as f:
    tree = ast.parse(f.read())
for n in ast.walk(tree):
    if isinstance(n, ast.ClassDef):
        methods = [x.name for x in n.body if isinstance(x, (ast.FunctionDef, ast.AsyncFunctionDef))]
        print(f"{n.name}: {methods}")
