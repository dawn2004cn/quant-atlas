#!/usr/bin/env python3
"""比较当前文件与git中的原始文件"""

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

files_to_check = [
    'app/presentation/web/templates/architecture_roadmap.html',
    'app/presentation/web/templates/integration_hub.html',
]

for filepath in files_to_check:
    print(f'文件: {filepath}')

    # 获取git中的原始内容
    result = subprocess.run(
        ['git', 'show', f'HEAD:{filepath}'],
        capture_output=True,
        check=True
    )
    git_data = result.stdout

    # 获取当前文件内容
    current_data = Path(filepath).read_bytes()

    print(f'  git文件大小: {len(git_data)}')
    print(f'  当前文件大小: {len(current_data)}')
    print(f'  是否相同: {git_data == current_data}')

    # 如果不同，找出差异位置
    if git_data != current_data:
        min_len = min(len(git_data), len(current_data))
        for i in range(min_len):
            if git_data[i] != current_data[i]:
                print(f'  差异在字节位置 {i}:')
                print(f'    git: {hex(git_data[i])} ({git_data[i]})')
                print(f'    当前: {hex(current_data[i])} ({current_data[i]})')
                # 查看上下文
                start = max(0, i - 10)
                end = min(min_len, i + 10)
                print(f'    git上下文: {git_data[start:end]}')
                print(f'    当前上下文: {current_data[start:end]}')
                break

    print()
