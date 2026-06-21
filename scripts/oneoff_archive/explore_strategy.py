import os
path = r'E:\project\workspace\myrepo\quant-atlas\app\modules\strategy\services'
if os.path.exists(path):
    print(os.listdir(path))
else:
    print(f'Path not found: {path}')
