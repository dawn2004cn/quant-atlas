"""Phase 1.2: Fix non-UTF-8 files by converting from GBK to UTF-8."""
from __future__ import annotations

import os

def is_utf8(filepath: str) -> bool:
    """Check if file is valid UTF-8."""
    try:
        with open(filepath, encoding="utf-8") as f:
            f.read()
        return True
    except UnicodeDecodeError:
        return False

def fix_file(filepath: str) -> bool:
    """Try to fix encoding by reading as GBK and writing as UTF-8."""
    try:
        # Read as binary
        with open(filepath, "rb") as f:
            raw = f.read()
        
        # Try to decode as GBK
        try:
            content = raw.decode("gbk")
        except UnicodeDecodeError:
            # Try other common encodings
            try:
                content = raw.decode("gb2312")
            except UnicodeDecodeError:
                try:
                    content = raw.decode("latin-1")
                except UnicodeDecodeError:
                    return False  # Cannot decode
        
        # Write back as UTF-8
        with open(filepath, "w", encoding="utf-8", newline="") as f:
            f.write(content)
        return True
    except Exception as e:
        print(f"Error processing {filepath}: {e}")
        return False

def main():
    fixed = []
    failed = []
    
    for dirpath, dirnames, filenames in os.walk("app"):
        if "__pycache__" in dirpath:
            continue
        for filename in filenames:
            if not filename.endswith(".py"):
                continue
            path = os.path.join(dirpath, filename)
            
            if not is_utf8(path):
                if fix_file(path):
                    fixed.append(path)
                else:
                    failed.append(path)
    
    print(f"Fixed {len(fixed)} files:")
    for f in fixed:
        print(f"  {os.path.relpath(f)}")
    
    if failed:
        print(f"\nFailed {len(failed)} files:")
        for f in failed:
            print(f"  {os.path.relpath(f)}")

if __name__ == "__main__":
    main()