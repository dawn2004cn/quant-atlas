import sys
import subprocess

result = subprocess.run([
    sys.executable, '-B', '-c',
    'from app import create_app; print("OK")'
], capture_output=True)

print('stdout:', result.stdout.decode())
print('stderr:', result.stderr.decode()[:500] if result.stderr else 'none')
print('return code:', result.returncode)