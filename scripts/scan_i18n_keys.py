import re
import os
import json
from pathlib import Path

def scan_keys():
    template_dir = Path("app/presentation/web/templates")
    # Matches {{ _('key') }} or {{ _("key") }}
    pattern = re.compile(r'\{\{\s*_\(\s*[\'\"](.*?)[\'\"]\s*\)\s*\}\}')
    
    referenced_keys = set()
    for root, _, files in os.walk(template_dir):
        for f in files:
            if f.endswith(".html"):
                path = Path(root) / f
                with open(path, "r", encoding="utf-8", errors="ignore") as file:
                    content = file.read()
                    matches = pattern.findall(content)
                    referenced_keys.update(matches)
    
    return sorted(list(referenced_keys))

def update_zh_json(keys):
    json_path = Path("locales/zh.json")
    if json_path.exists():
        with open(json_path, "r", encoding="utf-8") as f:
            current_data = json.load(f)
    else:
        current_data = {}

    # Flatten helper to check existence
    def get_flattened_keys(d, prefix=""):
        res = []
        for k, v in d.items():
            full_key = f"{prefix}.{k}" if prefix else k
            if isinstance(v, dict):
                res.extend(get_flattened_keys(v, full_key))
            else:
                res.append(full_key)
        return res

    existing_flat_keys = set(get_flattened_keys(current_data))
    missing_keys = [k for k in keys if k not in existing_flat_keys]
    
    print(f"Total referenced: {len(keys)}")
    print(f"Missing in zh.json: {len(missing_keys)}")
    
    # Auto-populate missing keys with logic guessed from key name
    for mk in missing_keys:
        parts = mk.split(".")
        d = current_data
        for p in parts[:-1]:
            if p not in d or not isinstance(d[p], dict):
                d[p] = {}
            d = d[p]
        
        # Guessed label: capitalize last part and replace _ with space
        label = parts[-1].replace("_", " ").capitalize()
        d[parts[-1]] = f"[MISSING] {label}"

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(current_data, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    found_keys = scan_keys()
    update_zh_json(found_keys)
