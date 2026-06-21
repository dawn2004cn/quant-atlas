import os

base = r'E:\project\workspace\myrepo\quant-atlas\app\presentation\web\templates'
for f in os.listdir(base):
    if f.startswith('self') or 'Stocks' in f:
        path = os.path.join(base, f)
        size = os.path.getsize(path)
        print(f'{f}: {size} bytes')