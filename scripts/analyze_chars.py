#!/usr/bin/env python3
"""分析不可打印字符的具体类型"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

templates_dir = Path('app/presentation/web/templates')

# 只检查问题较多的文件
problem_files = [
    'architecture_roadmap.html',
    'integration_hub.html',
    'retail_assistant.html',
    'observability.html',
    'capabilities.html',
    'profile.html',
    'professional_workbench.html',
    'optimize.html',
    'stocks_manage.html',
    'users_manage.html',
]

output_lines = []

for filename in problem_files:
    filepath = templates_dir / filename
    if not filepath.exists():
        continue

    content = filepath.read_text(encoding='utf-8')

    char_types = {}
    positions = []

    for i, char in enumerate(content):
        if not char.isprintable() and char not in '\n\r\t ':
            char_code = ord(char)
            char_hex = f'U+{char_code:04X}'

            # 分类
            if char_code == 0x202F:
                char_type = 'NARROW NO-BREAK SPACE (U+202F)'
            elif char_code == 0x00A0:
                char_type = 'NO-BREAK SPACE (U+00A0)'
            elif char_code == 0xFEFF:
                char_type = 'ZERO WIDTH NO-BREAK SPACE (BOM)'
            elif 0x2000 <= char_code <= 0x200F:
                char_type = f'ZERO WIDTH SPACE (U+{char_code:04X})'
            elif 0x2010 <= char_code <= 0x201F:
                char_type = f'PUNCTUATION (U+{char_code:04X})'
            elif 0x2020 <= char_code <= 0x202F:
                char_type = f'SPECIAL SPACE (U+{char_code:04X})'
            else:
                char_type = f'UNKNOWN (U+{char_code:04X})'

            if char_type not in char_types:
                char_types[char_type] = 0
            char_types[char_type] += 1

            if len(positions) < 5:
                line_num = content.count('\n', 0, i) + 1
                context = content[max(0, i-15):min(len(content), i+15)]
                positions.append(f'行{line_num}: "{context}"')

    output_lines.append(f'文件: {filename}')
    for char_type, count in char_types.items():
        output_lines.append(f'  {char_type}: {count}个')
    for pos in positions:
        output_lines.append(f'  示例: {pos}')
    output_lines.append('')

output_file = Path('scripts/html_chars_report.txt')
output_file.write_text('\n'.join(output_lines), encoding='utf-8')
print(f'报告已写入: {output_file}')
