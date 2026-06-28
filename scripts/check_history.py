#!/usr/bin/env python3
"""检查历史提交中的文件内容"""

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

filepath = 'app/presentation/web/templates/architecture_roadmap.html'

# 检查第一次提交
result = subprocess.run(
    ['git', 'show', f'abe6208d7:{filepath}'],
    capture_output=True,
    check=True
)
data = result.stdout

print(f'历史提交文件大小: {len(data)}')
print(f'前200字节: {data[:200]}')

# 检查第3行
txt = data.decode('utf-8')
lines = txt.split('\n')
if len(lines) > 2:
    print(f'\n第3行标题: {lines[2]}')

# 对比当前提交
result2 = subprocess.run(
    ['git', 'show', f'HEAD:{filepath}'],
    capture_output=True,
    check=True
)
data2 = result2.stdout
print(f'\nHEAD文件大小: {len(data2)}')
print(f'是否相同: {data == data2}')
