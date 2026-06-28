#!/usr/bin/env python3
"""Automatically convert onclick handlers to data-* attributes + delegated events."""
import re
from pathlib import Path

# Skip list
SKIP_FILES = {
    "static/h603799_kline.html",
}

# The global delegated listener
DELEGATED_LISTENER = """
<script>
document.addEventListener('click', function(e) {
    const el = e.target.closest('[data-action]');
    if (!el) return;
    const fn = el.dataset.action;
    if (window[fn]) window[fn](el.dataset.arg || el.dataset.page || el.dataset.href || '');
});
</script>
"""

# Samples for pattern matching
SAMPLES = [
    # Sample 1: Simple argument
    (r'<[^>]+\bdata-action=["\']([^"\']+)["\'][^>]*data-arg=["\']([^"\']*)["\'][^>]*>',
     lambda m: f'<element data-action="{m.group(1)}" data-arg="{m.group(2)}" style="cursor:pointer">'),
]

def convert_file(filepath: Path) -> int:
    """Convert a single HTML file."""
    print(f"Processing: {filepath.name}")

    # Read content
    with open(filepath, encoding='utf-8') as f:
        content = f.read()

    original_len = len(content)
    changes = 0

    # Step 1: Convert onclick="functionName('arg')" → data-action="functionName" data-arg="arg"
    pattern1 = r'onclick=["\']([^"\']*?)["\']'
    if re.search(pattern1, content):
        content = re.sub(pattern1, lambda m: f'data-action={match.group(0)}', content)
        changes += 1

    # Step 2: Convert onclick="functionName()" → data-action="functionName"
    pattern2 = r'<[^>]+\bdata-action=["\']([^"\']+)["\'][^>]*>'
    if re.search(pattern2, content):
        content = re.sub(pattern2, lambda m: f'<element data-action="{m.group(1)}" style="cursor:pointer">', content)
        changes += 1

    # Step 3: Convert location.href patterns
    pattern3 = r'<[^>]*onclick=["\'][^"\']*location\.href=["\'][^"\']*/stock/[^\'\"]*["\'][^>]*>'
    if re.search(pattern3, content):
        content = re.sub(pattern3, lambda m: '<a href="TARGET">", actual href will be injected by Jinja', content)
        changes += 1

    # Step 4: Convert event.stopPropagation() + changePage patterns
    pattern4 = r'<[^>]*data-page=["\']([^"\']+)["\'][^>]*>'
    if re.search(pattern4, content):
        content = re.sub(pattern4, lambda m: f'<button data-page="{m.group(1)}">')
        changes += 1

    # Step 5: Append delegated listener if not present
    if DELEGATED_LISTENER not in content:
        # Find </body> or </html> and append
        if '</body>' in content:
            content = content.replace('</body>', f'{DELEGATED_LISTENER}\n</body>', 1)
        elif '</html>' in content:
            content = content.replace('</html>', f'{DELEGATED_LISTENER}\n</html>', 1)
        else:
            content = DELEGATED_LISTENER + '\n' + content
        changes += 1

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

    new_len = len(content)
    print(f"  -> Modified {changes} times")
    print(f"  -> Size: {original_len} → {new_len} bytes")
    return changes, new_len - original_len


if __name__ == '__main__':
    templates_dir = Path(r"E:\project\workspace\myrepo\quant-atlas\scripts\templates")

    all_files = list(templates_dir.glob('*.html'))
    print(f"Found {len(all_files)} HTML files\n")

    total_modified = 0
    total_size_change = 0

    for html_file in sorted(all_files):
        if html_file.name in SKIP_FILES:
            print(f"Skipping: {html_file.name} (in skip list)")
            continue

        try:
            changes, size_diff = convert_file(html_file)
            total_modified += changes
            total_size_change += size_diff
        except Exception as e:
            print(f"  ✗ ERROR: {e}")

    print(f"\n{'='*60}")
    print("Summary:")
    print(f"  Files modified: {total_modified}")
    print(f"  Total size change: {total_size_change:+} bytes")
