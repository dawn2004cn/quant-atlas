#!/usr/bin/env python3
"""直接检查文件的实际内容"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

filepath = Path('app/presentation/web/templates/architecture_roadmap.html')
data = filepath.read_bytes()

print(f'文件大小: {len(data)}')
print(f'前200字节: {data[:200]}')

# 尝试UTF-8解码
try:
    txt = data.decode('utf-8')
    print('\nUTF-8解码成功')
    print(f'前200字符: {txt[:200]}')

    # 检查不可打印字符
    non_printable = [(i, c, ord(c)) for i, c in enumerate(txt) if not c.isprintable() and c not in '\n\r\t ']
    print(f'\n不可打印字符: {len(non_printable)}个')
    for i, c, code in non_printable[:10]:
        print(f'  位置{i}: U+{code:04X} "{c}"')

except Exception as e:
    print(f'UTF-8解码失败: {e}')
