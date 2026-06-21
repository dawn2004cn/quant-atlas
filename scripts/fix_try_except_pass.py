"""Fix all try/except pass patterns in app/ directory by adding logger.warning before pass."""
import re
import os
import ast


def get_function_name_at_line(lines, line_num):
    """Find the enclosing function name for a given line number (0-indexed)."""
    for node in ast.walk(ast.parse(''.join(lines))):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            start = node.lineno - 1
            end = node.end_lineno if hasattr(node, 'end_lineno') else start + 10
            if start <= line_num <= end:
                return node.name
    return None


def ensure_logger(filepath, lines):
    """Ensure `import logging` and `logger = logging.getLogger(__name__)` are present."""
    has_import = any('import logging' in l for l in lines)
    has_logger = any(re.match(r'logger\s*=\s*logging\.getLogger', l) for l in lines)

    changes = []
    if not has_import:
        # Find a good spot after existing imports
        insert_at = 0
        for i, l in enumerate(lines):
            if l.startswith('import ') or l.startswith('from '):
                insert_at = i + 1
            elif l.strip() and not l.startswith('#') and not l.startswith('"') and not l.startswith("'") and insert_at > 0:
                break
        if insert_at == 0:
            # No imports yet, put at top
            insert_at = 0
        changes.append((insert_at, "import logging\n"))
        # Adjust insert_at since we just added a line
        if not has_logger:
            changes.append((insert_at + 1, f"logger = logging.getLogger(__name__)\n"))
    elif not has_logger:
        # Find a good spot after the last import line
        insert_at = 0
        for i, l in enumerate(lines):
            if l.startswith('import ') or l.startswith('from '):
                insert_at = i + 1
            elif l.strip() and not l.startswith('#') and not l.startswith('"') and not l.startswith("'") and insert_at > 0:
                break
        changes.append((insert_at, f"logger = logging.getLogger(__name__)\n"))

    # Apply changes in reverse order (to preserve indices)
    for idx, line in sorted(changes, key=lambda x: -x[0]):
        lines.insert(idx, line)
    return len(changes) > 0


def fix_file(filepath):
    with open(filepath, encoding='utf-8', errors='replace') as f:
        lines = f.readlines()

    orig = lines.copy()
    modified = False

    for i in range(len(lines)):
        except_match = re.match(r'(\s*)except\b(.+?):\s*(#.*)?$', lines[i])
        if not except_match:
            continue

        indent = except_match.group(1)
        exc_clause = except_match.group(2).strip()

        pass_on_next = False
        if 'pass' in lines[i]:
            # Same line: `except X: pass`
            pass
        elif i + 1 < len(lines) and re.match(r'\s*pass\s*(#.*)?$', lines[i + 1]):
            pass_on_next = True
        else:
            continue

        # Determine function name
        func_name = get_function_name_at_line(lines, i) or 'unknown'

        # Build warning line
        warning = f'{indent}    logger.warning("Suppressed exception in {func_name}", exc_info=True)\n'

        if pass_on_next:
            # Insert warning before the pass on next line
            lines.insert(i + 1, warning)
            modified = True
        else:
            # Same line: replace `pass` with warning + pass
            # e.g. `except Exception: pass` -> `except Exception: logger.warning(...); pass`
            new_line = re.sub(
                r'\bpass\b',
                f'logger.warning("Suppressed exception in {func_name}", exc_info=True); pass',
                lines[i]
            )
            lines[i] = new_line
            modified = True

    if modified:
        ensure_logger(filepath, lines)

    if modified:
        with open(filepath, 'w', encoding='utf-8', newline='') as f:
            f.writelines(lines)
        return True
    return False


def main():
    results = []
    for d, dirs, files in os.walk('app'):
        if '__pycache__' in d:
            continue
        for f in files:
            if not f.endswith('.py'):
                continue
            path = os.path.join(d, f)
            if fix_file(path):
                results.append(os.path.relpath(path))

    print(f"Files fixed: {len(results)}")
    for r in results:
        print(f"  {r}")


if __name__ == '__main__':
    main()
