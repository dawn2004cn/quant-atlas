import os

def find_file(name, start_path):
    for root, dirs, files in os.walk(start_path):
        if name in files:
            return os.path.join(root, name)
    return None

print(find_file('tdx_selector.py', r'E:\project\workspace\myrepo\quant-atlas'))
