import os
root = r'E:\project\workspace\myrepo\quant-atlas\infrastructure'
for root_dir, dirs, files in os.walk(root):
    for file in files:
        if file.endswith('.py'):
            print(os.path.join(root_dir, file))
