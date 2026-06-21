import ast
import os
import sys

class ContractAuditor(ast.NodeVisitor):
    def __init__(self, filename):
        self.filename = filename
        self.errors = []

    def visit_FunctionDef(self, node):
        # Check return type annotation
        if node.returns and isinstance(node.returns, ast.Name) and node.returns.id == 'dict':
            self.errors.append(f"Violation in {self.filename}:{node.lineno}: Method {node.name} returns 'dict'. Use DTO instead.")
        
        # Check input arguments for 'Any'
        for arg in node.args.args:
            if isinstance(arg.annotation, ast.Name) and arg.annotation.id == 'Any':
                self.errors.append(f"Violation in {self.filename}:{node.lineno}: Argument {arg.arg} is 'Any'. Use specific DTO.")
        
        self.generic_visit(node)

def audit_directory(path, baseline_path="scripts/violations_baseline.txt"):
    violations = []
    for root, _, files in os.walk(path):
        for file in files:
            if file.endswith(".py"):
                full_path = os.path.join(root, file)
                with open(full_path, "r", encoding="latin-1") as f:
                    try:
                        tree = ast.parse(f.read())
                        auditor = ContractAuditor(full_path)
                        auditor.visit(tree)
                        violations.extend(auditor.errors)
                    except SyntaxError:
                        continue
    
    # Load baseline
    baseline = set()
    if os.path.exists(baseline_path):
        with open(baseline_path, "r", encoding="latin-1") as f:
            for line in f:
                if line.strip(): baseline.add(line.strip())
                
    new_violations = [v for v in violations if v not in baseline]
    
    for v in new_violations:
        print(f"NEW VIOLATION: {v}")
        
    return len(new_violations)

if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "app/application/services"
    print(f"Auditing contracts in {target}...")
    count = audit_directory(target)
    if count > 0:
        print(f"\nAudit failed with {count} violations.")
        sys.exit(1)
    else:
        print("\nAudit passed! All services are compliant with DTO contracts.")
        sys.exit(0)
