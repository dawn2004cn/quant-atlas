import os
import glob

root_path = r'E:\project\workspace\myrepo\quant-atlas\app'
matches = []
for root, dirs, files in os.walk(root_path):
    for file in files:
        if file.endswith('.py'):
            full_path = os.path.join(root, file)
            with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                if '.db' in content or 'sqlite3.connect' in content:
                    matches.append(full_path)

print(f"Found {len(matches)} files with .db or sqlite3.connect:")
for m in matches:
    print(m)
