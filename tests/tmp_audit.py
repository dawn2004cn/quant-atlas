import re
from pathlib import Path
for p in sorted(Path('app/presentation/web/templates').rglob('*.html')):
    txt=p.read_text(encoding='utf-8', errors='ignore')
    count=txt.count('$.getJSON')+txt.count('$.ajax')+txt.count('fetch(')
    if count:
        print(f'{p.relative_to(".")} ajax/fetch calls: {count}')
    # spot missing error handling patterns
    has_catch=('catch(' in txt or '.fail(' in txt)
    if count and not has_catch:
        print(f'  WARN: no .catch/.fail on AJAX path')
    if 'loading' in txt and count>3:
        print('  INFO: loading indicator present')
