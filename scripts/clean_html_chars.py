#!/usr/bin/env python3
"""清理HTML文件中的不可打印字符（主要是BOM）"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

templates_dir = Path('app/presentation/web/templates')
html_files = list(templates_dir.rglob('*.html'))

fixed_count = 0
unchanged_count = 0

for html_file in html_files:
    content = html_file.read_bytes()

    # 检查是否有BOM
    has_bom = content.startswith(b'\xef\xbb\xbf')

    # 检查是否有其他不可打印字符
    has_non_printable = False
    if has_bom:
        text = content[3:].decode('utf-8')
    else:
        text = content.decode('utf-8')

    for c in text:
        if not c.isprintable() and c not in '\n\r\t ':
            has_non_printable = True
            break

    if has_bom or has_non_printable:
        # 移除BOM和不可打印字符
        if has_bom:
            content = content[3:]
            text = content.decode('utf-8')

        # 清理不可打印字符
        clean_text = ''.join(c for c in text if c.isprintable() or c in '\n\r\t ')
        html_file.write_text(clean_text, encoding='utf-8')
        fixed_count += 1
    else:
        unchanged_count += 1

print(f'清理完成: {fixed_count} 个文件已修复, {unchanged_count} 个文件未变更')
