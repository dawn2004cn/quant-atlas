"""Phase 1: Fix non-UTF-8 encoding and hardcoded IPs.

Phase 1.2 - Convert all non-UTF-8 Python files to UTF-8
Phase 1.3 - Replace hardcoded IPs with env vars"""

import re
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(SCRIPT_DIR)


def check_utf8(path):
    """Check if a file is valid UTF-8 by attempting to read it."""
    try:
        with open(path, 'r', encoding='utf-8') as f:
            f.read()
        return True
    except (UnicodeDecodeError, SyntaxError):
        return False


def detect_encoding(path):
    """Detect file encoding by trying common Chinese encodings."""
    with open(path, 'rb') as f:
        raw = f.read(5000)  # Read enough to detect
    
    encodings = ['gbk', 'gb2312', 'gb18030', 'latin-1']
    for enc in encodings:
        try:
            raw.decode(enc)
            return enc
        except:
            continue
    return None


def fix_encoding(path):
    """Convert a file from detected encoding to UTF-8."""
    enc = detect_encoding(path)
    if enc is None:
        return False
    
    with open(path, 'rb') as f:
        raw = f.read()
    
    try:
        text = raw.decode(enc)
    except:
        return False
    
    # Write as UTF-8
    with open(path, 'w', encoding='utf-8', newline='') as f:
        f.write(text)
    return True


def fix_hardcoded_ip(content):
    """Replace hardcoded Redis IPs with env var pattern."""
    replacements = [
        (r'redis://192\.168\.8\.103:6380/0', 'get_runtime("REDIS_URL", "")'),
        (r'redis://192\.168\.8\.103:6379/0', 'get_runtime("REDIS_URL", "")'),
    ]
    for pattern, replacement in replacements:
        if re.search(pattern, content) and 'get_runtime' not in content:
            content = re.sub(pattern, replacement, content)
    return content


def main():
    utf8_fixed = 0
    files_checked = 0
    
    for r, _, files in os.walk(BASE_DIR):
        if '__pycache__' in r or 'node_modules' in r or '.git' in r:
            continue
        for f in files:
            if not f.endswith('.py'):
                continue
            path = os.path.join(r, f)
            
            # Check encoding
            if not check_utf8(path):
                orig_size = os.path.getsize(path)
                if fix_encoding(path):
                    new_size = os.path.getsize(path)
                    utf8_fixed += 1
                    rel = os.path.relpath(path, BASE_DIR)
                    print(f"  ENC_FIX: {rel} ({orig_size} -> {new_size} bytes)")
            else:
                # Already UTF-8, still check for hardcoded IPs
                with open(path, 'r', encoding='utf-8') as fh:
                    content = fh.read()
                fixed = fix_hardcoded_ip(content)
                if fixed != content:
                    with open(path, 'w', encoding='utf-8', newline='') as fh:
                        fh.write(fixed)
                    rel = os.path.relpath(path, BASE_DIR)
                    print(f"  IP_FIX: {rel}")
    
    print(f"\nUTF-8 conversions: {utf8_fixed}")
    print(f"Files checked: {files_checked}")
    
    # Summary
    count_utf8 = 0
    count_gbk = 0
    for r, _, files in os.walk(BASE_DIR):
        if '__pycache__' in r or 'node_modules' in r or '.git' in r:
            continue
        for f in files:
            if not f.endswith('.py'):
                continue
            path = os.path.join(r, f)
            if check_utf8(path):
                count_utf8 += 1
            else:
                count_gbk += 1
    print(f"\nFinal: {count_utf8} UTF-8 files, {count_gbk} remaining non-UTF-8 files")


if __name__ == '__main__':
    main()