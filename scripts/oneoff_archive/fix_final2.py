"""Surgical fix: remove first duplicate import_model, keep register_node intact."""
PATH = "E:\\project\\workspace\\myrepo\\quant-atlas\\app\\modules\\system\\services\\institution_tier_service.py"

with open(PATH, "r", encoding="utf-8") as f:
    lines = f.readlines()

# Structure we want:
# L...: def _write_nodes -> body -> blank line
# L...: def export_model -> body -> blank line  
# L...: def import_model (KEEP THIS ONE)
# Then: def register_node (find the NEXT def after first import_model)
# ...: def heartbeat

# Find positions
export_line = None
import_line_1 = None
import_line_2 = None
register_line = None

for i, l in enumerate(lines):
    if "def export_model" in l:
        export_line = i
    if "def import_model" in l:
        if import_line_1 is None:
            import_line_1 = i
        else:
            import_line_2 = i
    if "def register_node" in l:
        register_line = i

print(f"export_model: L{export_line+1}")
print(f"import_model_1: L{import_line_1+1}")
print(f"import_model_2: L{import_line_2+1}")
print(f"register_node: L{register_line+1}")

# We need to REMOVE the first import_model and everything up to (but not including)
# the second import_model, EXCEPT that register_node falls between them.
# So we need to keep register_node.

# Lines to keep: 0..export_model+body, then second import_model..register_line-1
# Find: end of export_model body
# Find: end of first import_model body (= start of register_node)
# Find: end of register_node body (= start of heartbeat)

# Actually, simpler: just remove first import_model body 
# The first import_model body is from import_line_1 to register_line
# Keep: lines[0:export_end] + lines[import_line_2:]

# Find end of export_model (next def or blank line after body)
export_end = import_line_1  # first import_model is right after export_model
while export_end < len(lines) and lines[export_end].strip():
    export_end += 1
while export_end < len(lines) and not lines[export_end].strip():
    export_end += 1

# Check: are there stray lines between export_model and register_node?
print(f"\\nBetween export_model end ({export_end+1}) and register_node ({register_line+1}):")
for i in range(export_line, min(register_line + 5, len(lines))):
    print(f"  L{i+1}: {repr(lines[i])[:80]}")

# The issue is that after import_model_2, we'll have register_node 
# (which was BEFORE import_model_2, then import_model_2)
# Actually re-checking: import_line_1 < register_line < import_line_2
# So the order is: export --- import_1 --- register --- import_2
# We want: export --- import_2 --- register (but that would reverse order)
# Wait no, let me re-read the output

# Actually based on earlier output:
# L486: export_model ends
# L488: import_model_1 starts
# L504: import_model_1 ends
# L506: register_node starts  
# L524: register_node ends (but corrupted - has export_model docstring)
# L526: import_model_2 starts

# So the correct order should be: export --- import --- register
# The second import_model is the duplicate!

# Strategy: remove import_model at L526+, but fix register_node first?

# Let me check: which import_model has the correct body?
# Both look identical. The second one at L526 is the extra.

# Removal: lines L525 to L541 = import_model_2 (*find where next def starts)
import_2_end = import_line_2 + 1
while import_2_end < len(lines) and (lines[import_2_end].startswith(" ") or not lines[import_2_end].strip()):
    import_2_end += 1

print(f"\\nimport_model_2 at L{import_line_2+1} ends before L{import_2_end+1}")
print(f"next line: {repr(lines[import_2_end])[:80]}")

# Remove L(import_line_2) to L(import_2_end - 1) = the second import_model
new_lines = lines[:import_line_2] + lines[import_2_end:]

with open(PATH, "w", encoding="utf-8") as f:
    f.writelines(new_lines)

print(f"Written: {len(new_lines)} lines")

# Fix the corrupted register_node docstring
# The register_node at old L506 has """Export aggregated model for air-gapped transfer.""" 
# instead of """Register or refresh a deployment node."""
for i, l in enumerate(new_lines):
    if "def register_node" in l:
        # Check the docstring on the next line
        next_line = new_lines[i+1] if i+1 < len(new_lines) else ""
        if "Export aggregated model" in next_line:
            print(f"Fixing corrupted register_node docstring at L{i+2}")
            new_lines[i+1] = '        """Register or refresh a deployment node."""\n'
        break

with open(PATH, "w", encoding="utf-8") as f:
    f.writelines(new_lines)

import py_compile
py_compile.compile(PATH, doraise=True)
print("Compiles OK!")

import ast
with open(PATH, "r", encoding="utf-8") as f:
    tree = ast.parse(f.read())
for n in ast.walk(tree):
    if isinstance(n, ast.ClassDef):
        methods = [x.name for x in n.body if isinstance(x, (ast.FunctionDef, ast.AsyncFunctionDef))]
        dupes = {m for m in methods if methods.count(m) > 1}
        if dupes:
            print(f"WARNING: {n.name} has duplicates: {dupes}")
        print(f"{n.name}: {methods}")
