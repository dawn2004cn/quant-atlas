path = "E:\\project\\workspace\\myrepo\\quant-atlas\\app\\modules\\system\\services\\institution_tier_service.py"
with open(path, "r", encoding="utf-8") as f:
    lines = f.readlines()

# Only fix: merge the split string literal at L952-953
for i in range(len(lines)):
    line = lines[i]
    if "fh.write(json.dumps(record" in line:
        # Check if the \n got split across two lines
        if line.rstrip().endswith('+"') or line.rstrip().endswith('"+'):
            if i+1 < len(lines) and lines[i+1].strip() == '")':
                print(f"Merging split at L{i+1}-{i+2}: {repr(line)} + {repr(lines[i+1])}")
                lines[i] = line.rstrip() + '\\n")' + "\n"
                lines[i+1] = None

lines = [l for l in lines if l is not None]

with open(path, "w", encoding="utf-8") as f:
    f.writelines(lines)

print(f"Written: {len(lines)} lines")

import py_compile
py_compile.compile(path, doraise=True)
print("Compiles OK!")
