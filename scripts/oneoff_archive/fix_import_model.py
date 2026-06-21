import sys

PATH = "E:\\project\\workspace\\myrepo\\quant-atlas\\app\\modules\\system\\services\\institution_tier_service.py"

with open(PATH, "r", encoding="utf-8") as f:
    lines = f.readlines()

# Find import_model method
import_start = None
import_end = None
for i, l in enumerate(lines):
    if "def import_model" in l:
        import_start = i
    if import_start is not None and i > import_start:
        stripped = l.strip()
        if stripped.startswith("def ") or stripped.startswith("class ") or (stripped.startswith("# ") and "RBAC" in stripped):
            import_end = i
            break

print(f"import_model: L{import_start+1} to L{import_end}")

# Build correct body using filesystem pattern matching run_fedavg_round
fixed = [
    "    def import_model(self, model_name: str, export_data: dict) -> bool:\n",
    '        """Import model from air-gapped transfer."""\n',
    "        weights = export_data.get(\"weights\", {})\n",
    "        if not weights:\n",
    "            return False\n",
    "        out_path = self._models_dir / f\"{model_name.replace('/', '_')}.json\"\n",
    "        out_path.write_text(\n",
    "            json.dumps({\n",
    '                "model_name": model_name,\n',
    '                "weights": weights,\n',
    '                "version": export_data.get("version", 1),\n',
    '                "num_nodes": export_data.get("num_nodes", 0),\n',
    '                "performance_metrics": export_data.get("performance_metrics", {}),\n',
    "                \"imported_at\": datetime.now(timezone.utc).isoformat(),\n",
    "            }, ensure_ascii=False, indent=2),\n",
    '            encoding="utf-8",\n',
    "        )\n",
    '        logger.info("Model %s imported from air-gapped transfer (version=%s)",\n',
    "                   model_name, export_data.get(\"version\", 1))\n",
    "        return True\n",
]

print("Replacement:")
for l in fixed:
    print(f"  {repr(l)}")

lines[import_start:import_end] = fixed

with open(PATH, "w", encoding="utf-8") as f:
    f.writelines(lines)

print(f"Written: {len(lines)} lines")

import py_compile
py_compile.compile(PATH, doraise=True)
print("Compiles OK!")
