
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""修复所有文件中 from __future__ imports 的位置问题"""

import os
import sys

def fix_file(path):
    try:
        with open(path, 'r', encoding='utf-8') as fp:
            content = fp.read()
    except UnicodeDecodeError:
        try:
            with open(path, 'r', encoding='utf-8-sig') as fp:
                content = fp.read()
        except:
            return False
    
    lines = content.split('\n')
    if not lines:
        return False
    
    # 检查第一行是否已经是 from __future__
    if lines[0].strip().startswith('from __future__'):
        return False
    
    # 查找 from __future__ import annotations 的位置
    future_line = None
    future_idx = -1
    for i, line in enumerate(lines):
        if line.strip().startswith('from __future__ import annotations'):
            future_line = line
            future_idx = i
            break
    
    if future_idx == -1:
        return False
    
    # 将 from __future__ 移到第一行
    lines.pop(future_idx)
    lines.insert(0, future_line)
    
    # 写回文件
    try:
        with open(path, 'w', encoding='utf-8') as fp:
            fp.write('\n'.join(lines))
        print(f'修复: {path}')
        return True
    except:
        return False

def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    app_dir = os.path.join(base_dir, 'app')
    
    fixed_count = 0
    for root, dirs, files in os.walk(app_dir):
        for f in files:
            if f.endswith('.py'):
                path = os.path.join(root, f)
                if fix_file(path):
                    fixed_count += 1
    
    print(f'\n共修复 {fixed_count} 个文件')

if __name__ == '__main__':
    main()
