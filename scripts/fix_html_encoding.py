#!/usr/bin/env python3
"""修复HTML模板文件的编码问题：GBK→UTF-8转换并移除BOM"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

templates_dir = Path('app/presentation/web/templates')
html_files = list(templates_dir.rglob('*.html'))

fixed_count = 0
failed_count = 0
unchanged_count = 0

output_lines = []
output_lines.append('HTML编码修复报告')
output_lines.append('=' * 80)
output_lines.append('')

for html_file in html_files:
    try:
        # 先尝试UTF-8读取
        content = html_file.read_bytes()

        # 检查是否有BOM
        has_bom = content.startswith(b'\xef\xbb\xbf')

        # 尝试判断编码
        try:
            # 先尝试GBK解码
            decoded = content.decode('gbk')
            # 如果解码成功且包含中文字符，可能是GBK编码
            has_chinese = any('\u4e00' <= c <= '\u9fff' for c in decoded)

            if has_chinese:
                # 这是GBK编码的中文文件，需要转换为UTF-8
                # 去掉BOM（如果有）
                if has_bom:
                    content = content[3:]
                    decoded = content.decode('gbk')

                # 重新编码为UTF-8
                new_content = decoded.encode('utf-8')
                html_file.write_bytes(new_content)
                fixed_count += 1
                output_lines.append(f'✅ 已修复: {html_file.relative_to(templates_dir)}')
                continue
        except UnicodeDecodeError:
            pass

        # 如果是UTF-8但有BOM，移除BOM
        if has_bom:
            content = content[3:]
            html_file.write_bytes(content)
            fixed_count += 1
            output_lines.append(f'✅ 移除BOM: {html_file.relative_to(templates_dir)}')
            continue

        unchanged_count += 1

    except Exception as e:
        failed_count += 1
        output_lines.append(f'❌ 失败: {html_file.relative_to(templates_dir)} - {e}')

output_lines.append('')
output_lines.append(f'总计: {len(html_files)} 个文件')
output_lines.append(f'✅ 已修复: {fixed_count} 个')
output_lines.append(f'❌ 失败: {failed_count} 个')
output_lines.append(f'➖ 未变更: {unchanged_count} 个')

output_file = Path('scripts/html_fix_report.txt')
output_file.write_text('\n'.join(output_lines), encoding='utf-8')
print(f'修复完成！报告已写入: {output_file}')
print(f'已修复: {fixed_count} 个文件')
