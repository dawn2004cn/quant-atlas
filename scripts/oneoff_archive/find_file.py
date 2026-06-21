import os
target = "behavior_topology_guardian.py"
root = r'E:\project\workspace\myrepo\quant-atlas\app'
matches = []
for root_dir, dirs, files in os.walk(root):
    for file in files:
        if file == target:
            matches.append(os.path.join(root_dir, file))
print(matches)
