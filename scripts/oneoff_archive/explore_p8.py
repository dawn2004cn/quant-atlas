import pathlib, re

targets = {
    "MetaArbiterService": "app/application/services/orchestration/meta_arbiter_service.py",
    "DataTruthGuardianService": "app/application/services/quality/data_truth_guardian_service.py",
    "CollaborationBlackboard": None,
    "DecisionContextDTO": None,
    "panorama": None,
    "full-trace": None,
}

# Find files
for name in targets:
    result = None
    for f in pathlib.Path("app").rglob("*.py"):
        if f.name == "__init__.py": continue
        try:
            if name.lower() in f.read_text(encoding="utf-8", errors="ignore").lower():
                result = str(f)
                break
        except: continue
    print(f"{name} -> {result or 'NOT FOUND'}")
