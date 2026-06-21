"""Fix GBK corruption in quote_aggregator.py line 36"""
import re

f = 'app/infrastructure/realtime/quote_aggregator.py'
with open(f, 'rb') as fh:
    raw = fh.read()

content = raw.decode('utf-8', errors='replace')

# Fix corrupted enum line
content = content.replace(
    '  EALTIME = "realtime"  # 实时推    PUS "push"          # WebSocket 推    POLL poll"',
    '    REALTIME = "realtime"  # 实时推送\n    PUSH = "push"          # WebSocket 推送\n    POLL = "poll"          # 定时拉取'
)

# Ensure import
if 'RedisClientPool' in content and 'from app.infrastructure.redis_client' not in content:
    lines = content.split('\n')
    for i, l in enumerate(lines):
        if 'from app.core.logger' in l:
            lines.insert(i, 'from app.infrastructure.redis_client import RedisClientPool')
            break
    content = '\n'.join(lines)

with open(f, 'w', encoding='utf-8') as fh:
    fh.write(content)

print('Fixed quote_aggregator.py')

# Now compile-check
import py_compile
try:
    py_compile.compile(f, doraise=True)
    print('Compile OK')
except py_compile.PyCompileError as e:
    print(f'Compile FAIL: {e}')