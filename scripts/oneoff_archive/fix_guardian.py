import pathlib

# Fix DataTruthGuardian patching
guardian_path = pathlib.Path("app/application/services/system/data_truth_guardian_service.py")
guardian_code = guardian_path.read_text(encoding="utf-8")

# Find the last method in the class and append after it
# The class has methods like start_auto_heal, _on_deviation_auto_heal, get_manifest, etc.
# Find where the class body ends (last dedented line before next top-level)

lines = guardian_code.splitlines(keepends=True)
last_method_line = None
class_indent = None
for i in range(len(lines) - 1, -1, -1):
    stripped = lines[i].strip()
    if stripped.startswith("class ") and stripped.endswith(":"):
        # Found class declaration - methods should be indented
        if i + 1 < len(lines):
            for j in range(i + 1, len(lines)):
                if lines[j].strip() and not lines[j].startswith(" ") and not lines[j].startswith("\n"):
                    # This is a top-level statement after the class
                    class_indent = len(lines[i]) - len(lines[i].lstrip())
                    last_method_line = j - 1
                    break
        break

if last_method_line is None:
    # Fallback: find last blank line before next top-level
    for i in range(len(lines) - 1, -1, -1):
        if lines[i].strip() == "" and i > 0 and not lines[i-1].startswith(" "):
            last_method_line = i
            break

print(f"Inserting at line {last_method_line} (indent={class_indent})")

add_method_lines = [
    "\n",
    " " * class_indent + "def publish_anomaly_to_blackboard(\n",
    " " * (class_indent + 4) + "self,\n",
    " " * (class_indent + 4) + "*,\n",
    " " * (class_indent + 4) + "team_id: int = 0,\n",
    " " * (class_indent + 4) + "blackboard_service: Any | None = None,\n",
    " " * (class_indent + 4) + "symbol: str = \"\",\n",
    " " * (class_indent + 4) + "anomaly_type: str = \"data_deviation\",\n",
    " " * (class_indent + 4) + "narrative: str = \"\",\n",
    " " * (class_indent + 4) + "payload: dict | None = None,\n",
    " " * (class_indent + 4) + ") -> dict[str, Any]:\n",
    ' ' * (class_indent + 8) + '"""Publish a data anomaly alert to the collaboration blackboard."""\n',
    " " * (class_indent + 8) + "if blackboard_service is None:\n",
    ' ' * (class_indent + 12) + 'return {"ok": False, "error": "blackboard_unavailable"}\n',
    " " * (class_indent + 8) + "try:\n",
    " " * (class_indent + 12) + "entry = blackboard_service.submit_note(\n",
    " " * (class_indent + 16) + "team_id=team_id,\n",
    " " * (class_indent + 16) + "user_id=0,\n",
    ' ' * (class_indent + 16) + 'evidence_key=f"data_truth_guardian.{anomaly_type}",\n',
    " " * (class_indent + 16) + "evidence_value=narrative[:500] if narrative else anomaly_type,\n",
    ' ' * (class_indent + 16) + 'agent_role="data_truth_guardian",\n',
    " " * (class_indent + 16) + "symbol=symbol or None,\n",
    ' ' * (class_indent + 16) + 'strength="strong",\n',
    " " * (class_indent + 16) + "narrative=narrative or f\"Data anomaly: {anomaly_type}\",\n",
    " " * (class_indent + 16) + "payload=payload or {},\n",
    " " * (class_indent + 12) + ")\n",
    ' ' * (class_indent + 12) + 'logger.info("Guardian anomaly blackboard: %s", anomaly_type)\n',
    ' ' * (class_indent + 12) + 'return {"ok": True, "entry": entry}\n',
    " " * (class_indent + 8) + "except Exception as exc:\n",
    ' ' * (class_indent + 12) + 'logger.warning("Guardian blackboard: %s", exc)\n',
    ' ' * (class_indent + 12) + 'return {"ok": False, "error": str(exc)}\n',
]

lines[last_method_line:last_method_line] = add_method_lines
guardian_path.write_text("".join(lines), encoding="utf-8")
print("2. Patched DataTruthGuardianService")
