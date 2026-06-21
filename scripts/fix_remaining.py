"""Fix the remaining corrupted docstrings in 4 files."""
from __future__ import annotations

import os

# 1. quote_aggregator.py: line 195 indentation (should be 8 spaces)
lines = []
with open('app/infrastructure/realtime/quote_aggregator.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()
# line numbers are 1-indexed
lines[194] = '        self._running = True\n'
with open('app/infrastructure/realtime/quote_aggregator.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)
print('Fixed quote_aggregator.py line 195')

# 2. redis_executor.py: line 715 docstring - replace with sensible English
lines = []
with open('app/infrastructure/execution/driver/redis_executor.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()
lines[714] = '        """Simulated trade execution"""\n'
with open('app/infrastructure/execution/driver/redis_executor.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)
print('Fixed redis_executor.py line 715')

# 3. tracing.py: line 601 marker assignment - fix unicode
lines = []
with open('app/infrastructure/tracing.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()
lines[600] = '            marker = "✗" if err else "✓"\n'
with open('app/infrastructure/tracing.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)
print('Fixed tracing.py line 601')

# 4. order_persistence.py: line 769 docstring - replace with sensible English
lines = []
with open('app/domain/trading/order_persistence.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()
lines[768] = '        """Get global portfolio snapshot"""\n'
with open('app/domain/trading/order_persistence.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)
print('Fixed order_persistence.py line 769')

print('All 4 files fixed.')