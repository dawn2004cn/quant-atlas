#!/usr/bin/env python3
"""详细检测HTML文件中的乱码问题"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

templates_dir = Path('app/presentation/web/templates')
html_files = list(templates_dir.rglob('*.html'))

output_lines = []
output_lines.append(f'发现 {len(html_files)} 个HTML文件')
output_lines.append('')

problem_files = []

for html_file in html_files:
    try:
        content = html_file.read_text(encoding='utf-8')

        issues = []

        # 检查\ufffd字符
        if '\ufffd' in content:
            count = content.count('\ufffd')
            # 找到位置
            positions = []
            idx = 0
            while True:
                idx = content.find('\ufffd', idx)
                if idx == -1:
                    break
                # 获取上下文
                start = max(0, idx - 20)
                end = min(len(content), idx + 20)
                context = content[start:end].replace('\ufffd', '[REPLACEMENT_CHAR]')
                line_num = content.count('\n', 0, idx) + 1
                positions.append(f'行{line_num}: ...{context}...')
                idx += 1
            issues.append(f'包含 {count} 个\\ufffd替换字符: {", ".join(positions[:5])}')

        # 检查其他不可打印字符（除了常见的空白字符）
        non_printable = []
        for i, char in enumerate(content):
            if not char.isprintable() and char not in '\n\r\t ':
                non_printable.append((i, char))

        if non_printable:
            issues.append(f'包含 {len(non_printable)} 个不可打印字符')

        # 检查编码问题（如GBK编码的中文被错误解码）
        # 尝试检测常见的编码错误模式
        gbk_errors = re.findall(r'[\x80-\xff][\x80-\xff]', content)
        if len(gbk_errors) > 10:
            issues.append(f'可能存在GBK编码错误（检测到{len(gbk_errors)}个双字节序列）')

        if issues:
            rel_path = html_file.relative_to(templates_dir.parent.parent.parent)
            problem_files.append((rel_path, issues))

    except UnicodeDecodeError as e:
        problem_files.append((html_file.relative_to(templates_dir.parent.parent.parent), [f'UTF-8解码失败: {e}']))
    except Exception as e:
        problem_files.append((html_file.relative_to(templates_dir.parent.parent.parent), [f'读取失败: {e}']))

if problem_files:
    output_lines.append(f'发现 {len(problem_files)} 个有问题的文件:')
    output_lines.append('=' * 100)
    for rel_path, issues in problem_files:
        output_lines.append(f'文件: {rel_path}')
        for issue in issues:
            output_lines.append(f'  → {issue}')
        output_lines.append('')
else:
    output_lines.append('所有文件编码正常')

output_file = Path('scripts/html_encoding_report.txt')
output_file.write_text('\n'.join(output_lines), encoding='utf-8')
print(f'报告已写入: {output_file}')
