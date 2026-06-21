"""Fix routes that were corrupted by script (replaced . with / in imports)."""

import glob
import os

os.chdir(r"E:\project\workspace\myrepo\quant-atlas")

fixed = 0
for filepath in glob.glob("app/presentation/api/routes_v1_*.py"):
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    original = content
    # Fix Windows path separators that made invalid Python: app.modules/system/ -> app.modules.system.
    # These were produced by the previous script that replaced . with /
    content = content.replace("app.modules/", "app.modules.")
    content = content.replace("app.modules.", "app.modules.")  # double-check no double replacement

    if content != original:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        fixed += 1

print(f"Fixed {fixed} files")
