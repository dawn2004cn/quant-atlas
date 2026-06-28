#!/usr/bin/env python3
"""批量恢复被破坏的HTML文件"""

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

templates_dir = Path('app/presentation/web/templates')
html_files = list(templates_dir.rglob('*.html'))

problem_files = []

for html_file in html_files:
    try:
        content = html_file.read_text(encoding='utf-8')
        # 检查是否有乱码特征
        has_garbage = False
        if '\ufffd' in content:
            has_garbage = True
        # 检查GBK乱码特征
        gbk_patterns = ['鏋舵瀯', '闆嗘垚', '涓灑', '鑳藉姏', '鎬昏', '鎵撳紑', '瑙傛祴', '鐮旂']
        for pat in gbk_patterns:
            if pat in content:
                has_garbage = True
                break
        if has_garbage:
            problem_files.append(html_file)
    except Exception:
        pass

output_lines = []
output_lines.append(f'发现 {len(problem_files)} 个有乱码的文件')

if not problem_files:
    output_lines.append('没有需要恢复的文件')
else:
    commit_hash = 'abe6208d7'
    fixed_count = 0
    failed_count = 0
    skipped_count = 0

    for html_file in problem_files:
        rel_path = str(html_file).replace('\\', '/')
        try:
            result = subprocess.run(
                ['git', 'show', f'{commit_hash}:{rel_path}'],
                capture_output=True,
                check=True
            )
            try:
                txt = result.stdout.decode('utf-8')
                if '鏋舵瀯' in txt or '\ufffd' in txt:
                    output_lines.append(f'SKIP: {rel_path} (历史版本也有乱码)')
                    skipped_count += 1
                    continue
            except:
                output_lines.append(f'SKIP: {rel_path} (历史版本解码失败)')
                skipped_count += 1
                continue

            html_file.write_bytes(result.stdout)
            fixed_count += 1
            output_lines.append(f'FIXED: {rel_path}')
        except subprocess.CalledProcessError:
            output_lines.append(f'FAILED: {rel_path} (git show失败)')
            failed_count += 1

    output_lines.append('')
    output_lines.append(f'总计: {len(problem_files)} 个文件')
    output_lines.append(f'FIXED: {fixed_count} 个')
    output_lines.append(f'FAILED: {failed_count} 个')
    output_lines.append(f'SKIPPED: {skipped_count} 个')

output_file = Path('scripts/html_restore_report.txt')
output_file.write_text('\n'.join(output_lines), encoding='utf-8')
print(f'Report written to: {output_file}')
