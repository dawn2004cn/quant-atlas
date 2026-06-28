#!/usr/bin/env python3
"""对比git和磁盘上的文件字节"""

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

filepath = 'app/presentation/web/templates/architecture_roadmap.html'

# 获取git中的内容
git_result = subprocess.run(
    ['git', 'show', f'HEAD:{filepath}'],
    capture_output=True,
    check=True
)
git_data = git_result.stdout

# 获取当前磁盘内容
current_data = Path(filepath).read_bytes()

print(f'git文件大小: {len(git_data)}')
print(f'当前文件大小: {len(current_data)}')

# 对比前200字节
print(f'\ngit前100字节: {git_data[:100]}')
print(f'当前前100字节: {current_data[:100]}')

# 查找差异
min_len = min(len(git_data), len(current_data))
diff_count = 0
first_diff_pos = -1
for i in range(min_len):
    if git_data[i] != current_data[i]:
        diff_count += 1
        if first_diff_pos == -1:
            first_diff_pos = i
            print(f'\n第一个差异位置: {i}')
            print(f'  git: {hex(git_data[i])}')
            print(f'  当前: {hex(current_data[i])}')
            start = max(0, i - 20)
            end = min(min_len, i + 20)
            print(f'  git上下文: {git_data[start:end]}')
            print(f'  当前上下文: {current_data[start:end]}')

print(f'\n差异字节数: {diff_count}')
print(f'文件末尾差异: {len(git_data) != len(current_data)}')
