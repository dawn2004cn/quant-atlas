PATH = "E:\\project\\workspace\\myrepo\\quant-atlas\\app\\modules\\system\\services\\institution_tier_service.py"

with open(PATH, "r", encoding="utf-8") as f:
    lines = f.readlines()

# Find corrupted register_node (L508+) and replace with correct body
register_idx = None
heartbeat_idx = None
for i, l in enumerate(lines):
    if "def register_node" in l:
        register_idx = i
    if "def heartbeat" in l:
        heartbeat_idx = i
        break

print(f"register_node at L{register_idx+1}, heartbeat at L{heartbeat_idx+1}")

# Correct register_node body
fixed = [
    "    def register_node(self, node_id: str, name: str, mode: str = \"federated\") -> DeploymentNode:\n",
    '        """Register or refresh a deployment node."""\n',
    "        nodes = self._load_nodes_map()\n",
    "        node = DeploymentNode(node_id=node_id, name=name, mode=mode)\n",
    "        nodes[node_id] = node\n",
    "        self._write_nodes(nodes)\n",
    '        logger.info("Deployment node registered: %s (%s, mode=%s)", node_id, name, mode)\n',
    "        return node\n",
]

# Replace lines from register_idx to heartbeat_idx
lines[register_idx:heartbeat_idx] = fixed

with open(PATH, "w", encoding="utf-8") as f:
    f.writelines(lines)

print(f"Written: {len(lines)} lines")

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
        label = f" [DUP: {dupes}]" if dupes else ""
        print(f"  {n.name}: {methods}{label}")
