"""One-off: extract file backend + compact order_persistence.py via AST."""

from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TARGET = ROOT / "app/domain/trading/order_persistence.py"

PATCHED_METHODS = {
    "__init__": '''
def __init__(self, backend: str = "file", path: str = "data/orders", **kwargs):
    self._backend = backend
    self._path = Path(path)
    self._lock = threading.RLock()
    if backend == "file":
        self._path.mkdir(parents=True, exist_ok=True)
        self._state_file = self._path / "order_state.json"
        self._events_file = self._path / "order_events.jsonl"
        from .order_persistence_file import FileOrderPersistenceBackend
        self._file_backend = FileOrderPersistenceBackend(self._state_file, self._events_file)
''',
    "save_state": '''
def save_state(self, state: dict[str, Any]) -> bool:
    with self._lock:
        try:
            if self._backend == "file":
                return self._file_backend.save_state(state)
            if self._backend == "sqlite":
                return self._save_to_sqlite(state)
            if self._backend == "redis":
                return self._save_to_redis(state)
            logger.error("Unknown backend: %s", self._backend)
            return False
        except Exception as exc:
            logger.error("Failed to save state: %s", exc)
            return False
''',
    "load_state": '''
def load_state(self) -> dict[str, Any]:
    with self._lock:
        try:
            if self._backend == "file":
                return self._file_backend.load_state()
            if self._backend == "sqlite":
                return self._load_from_sqlite()
            if self._backend == "redis":
                return self._load_from_redis()
            return {}
        except Exception as exc:
            logger.error("Failed to load state: %s", exc)
            return {}
''',
    "save_event": '''
def save_event(self, event: dict[str, Any]) -> bool:
    with self._lock:
        try:
            if self._backend == "file":
                return self._file_backend.append_event(event)
            return True
        except Exception as exc:
            logger.error("Failed to save event: %s", exc)
            return False
''',
    "load_events": '''
def load_events(self, order_id: str | None = None) -> list[dict]:
    with self._lock:
        try:
            if self._backend == "file":
                return self._file_backend.load_events(order_id)
            return []
        except Exception as exc:
            logger.error("Failed to load events: %s", exc)
            return []
''',
}

REMOVE = {"_save_to_file", "_load_from_file", "_append_event", "_load_events"}


def main() -> None:
    src = TARGET.read_text(encoding="utf-8", errors="replace")
    tree = ast.parse(src)

    new_module_body: list[ast.stmt] = []
    for node in tree.body:
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
            continue
        if isinstance(node, ast.ClassDef) and node.name == "OrderPersistence":
            new_body: list[ast.stmt] = []
            for item in node.body:
                if isinstance(item, ast.FunctionDef) and item.name in REMOVE:
                    continue
                if isinstance(item, ast.FunctionDef) and item.name in PATCHED_METHODS:
                    new_body.append(ast.parse(PATCHED_METHODS[item.name]).body[0])
                else:
                    new_body.append(item)
            node.body = new_body
        new_module_body.append(node)

    module = ast.Module(
        body=[
            ast.parse('from __future__ import annotations').body[0],
            ast.Expr(value=ast.Constant("Order persistence — file/SQLite/Redis backends.")),
            *new_module_body,
        ],
        type_ignores=[],
    )
    ast.fix_missing_locations(module)
    compact = ast.unparse(module) + "\n"
    TARGET.write_text(compact, encoding="utf-8")
    print(f"Wrote {TARGET} ({len(compact.splitlines())} lines)")


if __name__ == "__main__":
    main()
