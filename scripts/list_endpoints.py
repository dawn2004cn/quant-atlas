import os
import re

endpoints = set()
for root, dirs, files in os.walk('app/presentation/web/templates'):
    for file in files:
        if file.endswith('.html'):
            with open(os.path.join(root, file), 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                matches = re.findall(r'[\'\"](/api/v1/[^\'\"]+)[\'\"]', content)
                endpoints.update(matches)
print(list(endpoints))
