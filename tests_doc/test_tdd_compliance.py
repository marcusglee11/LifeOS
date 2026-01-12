import pytest
import ast
import os
import yaml
import json
import hashlib

# Canonical Config Paths
ALLOWLIST_PATH = os.path.join(os.getcwd(), "tests_doc", "tdd_compliance_allowlist.yaml")
LOCKFILE_PATH = os.path.join(os.getcwd(), "tests_doc", "tdd_compliance_allowlist.lock.json")

# Violations configuration
FORBIDDEN_CALLS = {
    "time.time": "Use pinned clock helper",
    "time.monotonic": "Use pinned clock helper",
    "time.perf_counter": "Use pinned clock helper",
    "datetime.now": "Use pinned clock helper",
    "datetime.utcnow": "Use pinned clock helper",
    "datetime.datetime.now": "Use pinned clock helper",
    "datetime.date.today": "Use pinned clock helper",
    "uuid.uuid4": "Use deterministic UUID helper",
    "secrets.choice": "Use seeded random helper", 
    "exec": "Dynamic execution forbidden",
    "eval": "Dynamic execution forbidden",
    "__import__": "Dynamic import forbidden",
    "importlib.import_module": "Dynamic import forbidden",
}

FORBIDDEN_IMPORTS = {
    "requests": "No IO allowed in Core",
    "urllib": "No IO allowed in Core",
    "socket": "No IO allowed in Core",
    "random": "Use seeded random helper",
    "secrets": "Use seeded random helper",
    "numpy.random": "Use seeded random helper",
    "importlib": "Dynamic import forbidden",
}

class ViolationVisitor(ast.NodeVisitor):
    def __init__(self, filename):
        self.filename = filename
        self.violations = []

    def visit_Import(self, node):
        for alias in node.names:
            top_level_module = alias.name.split('.')[0]
            if top_level_module in FORBIDDEN_IMPORTS:
                self.violations.append(
                    (self.filename, node.lineno, f"Import '{alias.name}' forbidden. {FORBIDDEN_IMPORTS[top_level_module]}")
                )
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        if node.module:
            top_level_module = node.module.split('.')[0]
            if top_level_module in FORBIDDEN_IMPORTS:
                 self.violations.append(
                    (self.filename, node.lineno, f"Import from '{node.module}' forbidden. {FORBIDDEN_IMPORTS[top_level_module]}")
                )
        self.generic_visit(node)

    def visit_Call(self, node):
        func_name = self._get_full_func_name(node.func)
        if func_name:
             # Direct match (e.g. exec, eval, __import__)
             if func_name in FORBIDDEN_CALLS:
                 self.violations.append(
                    (self.filename, node.lineno, f"Call '{func_name}' forbidden. {FORBIDDEN_CALLS[func_name]}")
                 )
             else:
                 # Suffix match (e.g. time.time)
                 for banned in FORBIDDEN_CALLS:
                     if func_name.endswith(banned) and "." in banned: # Only match suffix if banned has dot
                         self.violations.append(
                            (self.filename, node.lineno, f"Call '{func_name}' forbidden. {FORBIDDEN_CALLS[banned]}")
                         )
        self.generic_visit(node)

    def _get_full_func_name(self, node):
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            value = self._get_full_func_name(node.value)
            if value:
                return f"{value}.{node.attr}"
        return None

def compute_file_hash(filepath):
    """Computes SHA256 hash of file content."""
    sha256_hash = hashlib.sha256()
    with open(filepath, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest().lower()

def load_and_verify_scope():
    """Loads scope from allowlist, verifying integrity via lockfile (Fail-Closed)."""
    if not os.path.exists(ALLOWLIST_PATH):
        pytest.fail(f"FAIL-CLOSED: Allowlist missing at {ALLOWLIST_PATH}")
    
    if not os.path.exists(LOCKFILE_PATH):
        pytest.fail(f"FAIL-CLOSED: Lockfile missing at {LOCKFILE_PATH}")

    # Verify Integrity
    current_hash = compute_file_hash(ALLOWLIST_PATH)
    with open(LOCKFILE_PATH, 'r') as f:
        lock_data = json.load(f)
    
    expected_hash = lock_data.get("allowlist_sha256", "").lower()
    if current_hash != expected_hash:
        pytest.fail(f"FAIL-CLOSED: Integrity Mismatch! Allowlist hash {current_hash} != {expected_hash} in lockfile.")

    print(f"\n[Integrity Verified] Allowlist SHA256: {current_hash}")
    
    with open(ALLOWLIST_PATH, 'r') as f:
        data = yaml.safe_load(f)
    
    return data.get("enforcement_scope", []), data.get("exemptions", [])

def scan_file(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        try:
            tree = ast.parse(f.read(), filename=filepath)
        except SyntaxError:
            return [(filepath, 0, "SyntaxError - could not parse")]
    
    visitor = ViolationVisitor(filepath)
    visitor.visit(tree)
    return visitor.violations

def test_core_tdd_compliance():
    repo_root = os.getcwd()
    scope_dirs, exemptions = load_and_verify_scope()
    
    all_violations = []

    for scope in scope_dirs:
        full_scope_path = os.path.join(repo_root, scope)
        if not os.path.exists(full_scope_path):
            print(f"Skipping missing scope directory: {scope}")
            continue

        for root, dirs, files in os.walk(full_scope_path):
            for file in files:
                if file.endswith(".py"):
                    full_path = os.path.join(root, file)
                    rel_path = os.path.relpath(full_path, repo_root).replace("\\", "/") # Normalize path
                    
                    if rel_path in exemptions:
                        continue
                        
                    all_violations.extend(scan_file(full_path))

    # Deterministic Reporting
    if all_violations:
        # Sort by (filename, line, message) for stable output
        all_violations.sort(key=lambda x: (x[0], x[1], x[2]))
        
        report_lines = ["\n[VIOLATION REPORT]"]
        for v in all_violations:
            report_lines.append(f"{v[0]}:{v[1]} {v[2]}")
        
        base_msg = "\n".join(report_lines)
        pytest.fail(base_msg)

# --- Negative Self-Tests ---

@pytest.mark.parametrize("code_snippet, expected_error_part", [
    ("import time\ntime.time()", "Call 'time.time' forbidden"),
    ("import datetime\ndatetime.datetime.now()", "Call 'datetime.datetime.now' forbidden"), 
    ("import requests", "Import 'requests' forbidden"),
    ("import urllib.request", "Import 'urllib.request' forbidden"),
    ("import uuid\nx = uuid.uuid4()", "Call 'uuid.uuid4' forbidden"),
    ("import secrets", "Import 'secrets' forbidden"),
    ("import time\ntime.monotonic()", "Call 'time.monotonic' forbidden"),
    ("eval('os.system(\"rm -rf\")')", "Call 'eval' forbidden"),
    ("exec('import os')", "Call 'exec' forbidden"),
    ("__import__('os')", "Call '__import__' forbidden"),
    ("import importlib\nimportlib.import_module('os')", "Import 'importlib' forbidden"),
])
def test_violations_detected_selftest(code_snippet, expected_error_part):
    try:
        tree = ast.parse(code_snippet, filename="<string>")
    except SyntaxError:
        pytest.fail("Invalid python code in test parametrization")
    
    visitor = ViolationVisitor("<string>")
    visitor.visit(tree)
    
    violations_str = [v[2] for v in visitor.violations]
    assert any(expected_error_part in v for v in violations_str), \
        f"Expected error '{expected_error_part}' not found in {violations_str}"
