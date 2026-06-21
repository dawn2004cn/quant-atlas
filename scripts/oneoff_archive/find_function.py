import os
target = "enrich_psychology_with_topology"
root = r'E:\project\workspace\myrepo\quant-atlas\app'
matches = []
for root_dir, dirs, files in os.walk(root):
    for file in files:
        if file.endswith('.py'):
            full_path = os.path.join(root_dir, file)
            try:
                with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                    if target in f.read():
                        matches.append(full_path)
            except Exception:
                pass
print(matches)
