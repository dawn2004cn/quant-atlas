import os
import re

root = r'E:\project\workspace\myrepo\quant-atlas\app'
pattern = re.compile(r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}') # Basic IP pattern
subnet_pattern = re.compile(r'\d{1,3}\.\d{1,3}\.\d{1,3}\.0') # Basic subnet pattern

matches = []
for root_dir, dirs, files in os.walk(root):
    for file in files:
        if file.endswith('.py'):
            full_path = os.path.join(root_dir, file)
            try:
                with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    if subnet_pattern.search(content):
                        matches.append(full_path)
            except Exception:
                pass
print(matches)
