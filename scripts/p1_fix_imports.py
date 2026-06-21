"""Clean up P1 fix artifacts: fix import placement and corrupted files."""
import os, re

# File 1: data_truth_guardian_service.py - logging import in wrong place
f = 'app/modules/system/services/system/data_truth_guardian_service.py'
with open(f, 'r', encoding='utf-8') as fh:
    lines = fh.readlines()
# Remove import logging placed inside class body
new_lines = []
skip_until = -1
for i, line in enumerate(lines):
    if i < skip_until:
        continue
    if 'import logging' in line and i > 5 and 'logger = logging' in lines[i+1:i+3]:
        # This was inserted in wrong place - skip it
        skip_until = i + 3
        continue
    new_lines.append(line)
with open(f, 'w', encoding='utf-8') as fh:
    fh.writelines(new_lines)
print(f'Fixed: {f}')

# File 2: shadow_routes.py - logging import in wrong place
f = 'app/presentation/api/v1/retail_assistant/shadow_routes.py'
with open(f, 'r', encoding='utf-8') as fh:
    lines = fh.readlines()
new_lines = []
skip_until = -1
for i, line in enumerate(lines):
    if i < skip_until:
        continue
    if 'import logging' in line and i > 5 and 'logger = logging' in lines[i+1:i+3]:
        skip_until = i + 3
        continue
    new_lines.append(line)
with open(f, 'w', encoding='utf-8') as fh:
    fh.writelines(new_lines)
print(f'Fixed: {f}')

# File 3: core/tracing/__init__.py - import logging in wrong place
f = 'app/core/tracing/__init__.py'
with open(f, 'r', encoding='utf-8') as fh:
    content = fh.read()
# Fix: remove extra import logging inside try block
content = re.sub(r'try:\s*\n\s+import logging\s*\n\s+logger = logging\.getLogger\(__name__\)\s*\n\s+except ImportError:', 
    'try:\n    import opentelemetry\n    logger = logging.getLogger(__name__)\nexcept ImportError:',
    content)
with open(f, 'w', encoding='utf-8') as fh:
    fh.write(content)
print(f'Fixed: {f}')

# File 4: core/llm_config.py - import logging in wrong place
f = 'app/core/llm_config.py'
with open(f, 'r', encoding='utf-8') as fh:
    content = fh.read()
# Find and fix misplaced logging imports
# Remove any import logging that appears after line 50 (not at module level)
lines = content.split('\n')
new_lines = []
i = 0
while i < len(lines):
    if i > 20 and ('import logging' in lines[i] and 'logger = logging' in lines[i+1:i+3]):
        # This is likely misplaced - remove
        i += 3
        continue
    new_lines.append(lines[i])
    i += 1
content = '\n'.join(new_lines)
with open(f, 'w', encoding='utf-8') as fh:
    fh.write(content)
print(f'Fixed: {f}')

print('Done fixing import placements.')