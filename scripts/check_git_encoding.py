#!/usr/bin/env python3
"""检查git中的原始文件编码"""

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

files_to_check = [
    'app/presentation/web/templates/architecture_roadmap.html',
    'app/presentation/web/templates/integration_hub.html',
    'app/presentation/web/templates/retail_assistant.html',
]

for filepath in files_to_check:
    print(f'文件: {filepath}')
    try:
        # 获取git中的原始内容
        result = subprocess.run(
            ['git', 'show', f'HEAD:{filepath}'],
            capture_output=True,
            check=True
        )
        data = result.stdout
        print(f'  文件大小: {len(data)}')
        print(f'  前100字节: {data[:100]}')

        # 尝试GBK解码
        try:
            txt = data.decode('gbk')
            has_chinese = any('\u4e00' <= c <= '\u9fff' for c in txt)
            print(f'  GBK解码: 成功，包含中文: {has_chinese}')
        except Exception as e:
            print(f'  GBK解码: 失败 - {e}')

        # 尝试UTF-8解码
        try:
            txt = data.decode('utf-8')
            has_chinese = any('\u4e00' <= c <= '\u9fff' for c in txt)
            print(f'  UTF-8解码: 成功，包含中文: {has_chinese}')
        except Exception as e:
            print(f'  UTF-8解码: 失败 - {e}')

        print()
    except subprocess.CalledProcessError as e:
        print(f'  获取失败: {e}')
        print()
