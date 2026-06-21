import json
import os
import re

def get_defined_keys(d, prefix=''):
    keys = []
    for k, v in d.items():
        full_key = f'{prefix}.{k}' if prefix else k
        if isinstance(v, dict):
            keys.extend(get_defined_keys(v, full_key))
        else:
            keys.append(full_key)
    return keys

def get_used_keys(path):
    keys = set()
    pattern = re.compile(r"_\s*\(\s*['\"]([^'\"]+)['\"]\s*\)")
    for root, dirs, files in os.walk(path):
        for f in files:
            if f.endswith('.html') or f.endswith('.py'):
                fp = os.path.join(root, f)
                try:
                    content = open(fp, encoding='utf-8').read()
                    found = pattern.findall(content)
                    keys.update(found)
                except:
                    pass
    return keys

zh = json.load(open('locales/zh.json', encoding='utf-8'))
zh_keys = set(get_defined_keys(zh))
used = get_used_keys('app')
missing = sorted(used - zh_keys)
print(f'Keys in code but missing in zh.json:')
for k in missing:
    print(f'  {k}')
print(f'Total: {len(missing)}')