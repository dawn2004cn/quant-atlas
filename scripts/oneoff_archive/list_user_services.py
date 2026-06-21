import os
root = r'E:\project\workspace\myrepo\quant-atlas\app\modules\user\services'
for root_dir, dirs, files in os.walk(root):
    print(f"Dir: {root_dir}")
    for f in files:
        print(f"  File: {f}")
