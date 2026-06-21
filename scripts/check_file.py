import os
base = r'E:\project\workspace\myrepo\quant-atlas\app\presentation\web\templates'
for f in sorted(os.listdir(base)):
    if 'self' in f.lower() or f.startswith('self'):
        path = os.path.join(base, f)
        size = os.path.getsize(path)
        data = open(path, 'rb').read(300)
        print(f'{f}: {size}b')
        print(f'  FIRST: {data[:200]}')
        print()