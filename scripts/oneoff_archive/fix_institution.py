"""Fix the mangled FederatedDeploymentService section in institution_tier_service.py."""
import hashlib
import json
import re

PATH = r'E:\\project\\workspace\\myrepo\\quant-atlas\\app\\modules\\system\\services\\institution_tier_service.py'

with open(PATH, 'r', encoding='utf-8') as f:
    src = src_orig = f.read()

# The corrupted section spans from just after "_load_nodes_map" body start to "def register_node"
# We need to find the exact boundaries and reconstruct

# Step 1: Find the broken _load_nodes_map / export_model / register_node cluster
load_nodes_start = src.find('def _load_nodes_map')
register_node = src.find('def register_node', load_nodes_start)

if load_nodes_start == -1 or register_node == -1:
    print('ERROR: Cannot find method boundaries')
    exit(1)

# Step 2: The correct reconstruct for the block from _load_nodes_map through register_node (exclusive)
# Find the actual _load_nodes_map body (before the corruption)  
# The original _load_nodes_map ended with:
#   data = json.loads(line)
#   node = DeploymentNode(**data)
#   nodes[node.node_id] = node
#   return nodes

# Find where the original _load_nodes_map body starts after "data = json.loads(line)"
data_line = src.find('data = json.loads(line)', load_nodes_start)
if data_line == -1:
    print('ERROR: Cannot find data = json.loads(line) in _load_nodes_map')
    exit(1)

# Everything from load_nodes_start up to after data = json.loads(line) is the valid start
before_load_nodes_map = src[:data_line]
after_data_line = src[data_line + len('data = json.loads(line)'):]

# Now we need to find where _load_nodes_map body continues and _write_nodes starts
# The corruption inserted export_model between the for loop body and the return
# Let's find _write_nodes and register_node
write_nodes_pos = src.find('def _write_nodes', load_nodes_start) 

# The original _load_nodes_map body in correct form should be:
load_nodes_map_body = '''    def _load_nodes_map(self) -> dict[str, DeploymentNode]:
        if not self._nodes_file.exists():
            return {}
        nodes: dict[str, DeploymentNode] = {}
        with self._nodes_file.open("r", encoding="utf-8") as fh:
            for line in fh:
                if not line.strip():
                    continue
                data = json.loads(line)
                node = DeploymentNode(**data)
                nodes[node.node_id] = node
        return nodes

    def _write_nodes(self, nodes: dict[str, DeploymentNode]) -> None:
        _lines = [json.dumps(n.__dict__, ensure_ascii=False) for n in nodes.values()]
        self._nodes_file.write_text("\\n".join(_lines) + ("\\n" if _lines else ""), encoding="utf-8")

'''

# New methods to add after _write_nodes and before register_node
new_methods = '''    def export_model(self, model_name: str, export_format: str = "json") -> dict | None:
        """Export aggregated model for air-gapped transfer."""
        model = self.get_aggregated_model(model_name)
        if model is None:
            return None
        export = {
            "model_name": model_name,
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "format": export_format,
            "version": model.get("version", 1),
            "weights": model.get("weights", {}),
            "num_nodes": model.get("num_nodes", 0),
            "performance_metrics": model.get("performance_metrics", {}),
            "signature": hashlib.sha256(
                json.dumps(model.get("weights", {}), sort_keys=True).encode("utf-8")
            ).hexdigest()[:16],
        }
        return export

    def import_model(self, model_name: str, export_data: dict) -> bool:
        """Import model from air-gapped transfer."""
        weights = export_data.get("weights", {})
        if not weights:
            return False
        self._models[model_name] = {
            "weights": weights,
            "version": export_data.get("version", 1),
            "num_nodes": export_data.get("num_nodes", 0),
            "performance_metrics": export_data.get("performance_metrics", {}),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        with self._store.open("w", encoding="utf-8") as fh:
            json.dump(self._models, fh, ensure_ascii=False, indent=2)
        logger.info("Model %s imported from air-gapped transfer (version=%s)",
                   model_name, export_data.get("version", 1))
        return True

'''

# Step 3: Find the end of the corrupted zone - either "    def register_node" or
# the next class definition or section header
register_node_pos = src.find('    def register_node', load_nodes_start)
# Find next section after load_nodes
sections = ['# ──', 'class ']
end_of_zone = len(src)
for s in sections:
    pos = src.find(s, load_nodes_start + 50)
    if pos != -1 and pos < end_of_zone:
        end_of_zone = pos

# The register_node should be the start of the next valid block
# Let's find it safely
rest_of_file = ''
if register_node_pos != -1:
    rest_of_file = src[register_node_pos:]  # "    def register_node..."
elif end_of_zone < len(src):
    rest_of_file = src[end_of_zone:]

# Step 4: Reconstruct
new_src = before_load_nodes_map + load_nodes_map_body + new_methods + rest_of_file

with open(PATH, 'w', encoding='utf-8') as f:
    f.write(new_src)

print(f'Fixed: {len(new_src)} bytes')
print(f'old: {len(src_orig)} bytes, new: {len(new_src)} bytes')
