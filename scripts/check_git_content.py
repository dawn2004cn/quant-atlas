#!/usr/bin/env python3
"""检查git中的文件内容"""

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

filepath = 'app/presentation/web/templates/architecture_roadmap.html'

# 获取git中的内容
result = subprocess.run(
    ['git', 'show', f'HEAD:{filepath}'],
    capture_output=True,
    check=True
)
data = result.stdout

print(f'git文件大小: {len(data)}')
print(f'前200字节: {data[:200]}')

# UTF-8解码
txt = data.decode('utf-8')
print(f'\n前200字符: {txt[:200]}')

# 检查第3行标题
lines = txt.split('\n')
if len(lines) > 2:
    print(f'\n第3行标题: {lines[2]}')
