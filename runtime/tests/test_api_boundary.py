
"""
Test to enforce API boundaries in the Runtime.
Ensures that runtime modules do not bypass API layers to access governance internals directly.
"""
import ast
import os
from pathlib import Path
from typing import List, Tuple

# Protected modules that should not be imported directly
PROTECTED_MODULES = [
    "runtime.governance",
    "runtime.amu0",
]

# Allowed access points
ALLOWED_IMPORTS = [
    "runtime.api",
    "runtime.api.governance_api",
    "runtime.api.runtime_api",
]

# Files exempt from these rules (the APIs themselves and tests)
EXEMPT_FILES = [
    "runtime/api/governance_api.py",
    "runtime/api/runtime_api.py",
    "runtime/governance/",  # Governance internals can import each other
    "runtime/amu0/",       # AMU0 internals can import each other
    "runtime/tests/",      # Tests verify internals
    "runtime/envelope/",   # Envelope is infrastructure, needs deep access
]

def check_imports(file_path: str) -> List[str]:
    """Check a file for illegal imports."""
    violations = []
    
    with open(file_path, "r", encoding="utf-8") as f:
        try:
            tree = ast.parse(f.read(), filename=file_path)
        except SyntaxError:
            return [f"SyntaxError parsing {file_path}"]

    for node in ast.walk(tree):
        # Check 'import runtime.governance...'
        if isinstance(node, ast.Import):
            for alias in node.names:
                for protected in PROTECTED_MODULES:
                    if alias.name.startswith(protected):
                        violations.append(f"Line {node.lineno}: Illegal import '{alias.name}'")

        # Check 'from runtime.governance import ...'
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                for protected in PROTECTED_MODULES:
                    if node.module.startswith(protected):
                        violations.append(f"Line {node.lineno}: Illegal import from '{node.module}'")
    
    return violations

def test_api_boundary_enforcement():
    """Scan runtime/ directory for API boundary violations."""
    runtime_root = Path("runtime").resolve()
    
    if not runtime_root.exists():
        # Fallback for test runner location
        runtime_root = Path.cwd() / "runtime"
    
    assert runtime_root.exists(), f"Could not find runtime root at {runtime_root}"
    
    all_violations = {}
    
    for python_file in runtime_root.rglob("*.py"):
        rel_path = python_file.relative_to(runtime_root.parent).as_posix()
        
        # Check exemptions
        is_exempt = False
        for exempt in EXEMPT_FILES:
            if rel_path.startswith(exempt) or exempt in rel_path:
                is_exempt = True
                break
        
        if is_exempt:
            continue
            
        # Check the file
        violations = check_imports(str(python_file))
        if violations:
            all_violations[rel_path] = violations
            
    # Report
    if all_violations:
        msg = "\nAPI Boundary Violations Found:\n"
        for fpath, errs in all_violations.items():
            msg += f"\nFile: {fpath}\n"
            for err in errs:
                msg += f"  {err}\n"
        
        assert False, msg

if __name__ == "__main__":
    test_api_boundary_enforcement()
