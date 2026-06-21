import os
path = r'E:\project\workspace\myrepo\quant-atlas\app\modules'
for root, dirs, files in os.walk(path):
    for file in files:
        if 'regime' in file.lower():
            print(os.path.join(root, file))
