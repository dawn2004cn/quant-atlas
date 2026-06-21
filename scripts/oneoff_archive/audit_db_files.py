import os
import glob

root_path = r'E:\project\workspace\myrepo\quant-atlas'
db_files = glob.glob(os.path.join(root_path, '**/*.db'), recursive=True)

print(f"Found {len(db_files)} .db files:")
for f in db_files:
    print(f)
