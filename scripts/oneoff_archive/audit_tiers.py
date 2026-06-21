import ast

files = [
    ("Retail", r"E:\project\workspace\myrepo\quant-atlas\app\modules\user\services\retail_tier_service.py"),
    ("Boutique", r"E:\project\workspace\myrepo\quant-atlas\app\modules\strategy\services\boutique_tier_service.py"),
    ("Investment", r"E:\project\workspace\myrepo\quant-atlas\app\modules\portfolio_risk\services\investment_tier_service.py"),
]

for tier, path in files:
    with open(path, "r", encoding="utf-8") as f:
        src = f.read()
    tree = ast.parse(src)
    print(f"\n{'='*60}")
    print(f"  {tier} Tier: {path.split(chr(92))[-1]} ({len(src)} chars)")
    print(f"{'='*60}")
    for n in ast.walk(tree):
        if isinstance(n, ast.ClassDef):
            methods = [x for x in n.body if isinstance(x, (ast.FunctionDef, ast.AsyncFunctionDef))]
            print(f"\n  {n.name} ({len(methods)} methods):")
            for m in methods:
                # Get first line of docstring
                doc = ""
                if m.body and isinstance(m.body[0], ast.Expr) and hasattr(m.body[0], "value") and hasattr(m.body[0].value, "value"):
                    doc = m.body[0].value.value[:60]
                args = [a.arg for a in m.args.args if a.arg != "self"]
                print(f"    def {m.name}({', '.join(args)})")
                if doc:
                    print(f"      -> {doc}")
