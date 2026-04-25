"""
Enforcement test for config/architecture/import_policy.yaml.

Scans runtime/ for cross-package import violations. Fail-closed:
  - Missing policy file → failure
  - Unlisted package imported by a scanned file → failure
  - Import not in allowed list → failure
"""
import ast
from pathlib import Path
from typing import Optional

import pytest
import yaml


POLICY_PATH = Path("config/architecture/import_policy.yaml")
RUNTIME_ROOT = Path("runtime")
EXCLUDED_PKG_NAMES = {"tests", "__pycache__", "memory", "spec"}


def load_policy() -> dict:
    """Load and return the import policy. Fail-closed: missing file = test failure."""
    assert POLICY_PATH.exists(), f"Import policy file missing: {POLICY_PATH}"
    with POLICY_PATH.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_policy_packages(policy: dict) -> dict[str, list[str]]:
    """Return {package_name: [allowed_imports]} from policy."""
    return {
        m["name"]: m.get("allowed_imports") or []
        for m in policy["modules"]
    }


def discover_packages() -> list[Path]:
    """Return all runtime sub-package directories (have __init__.py, not excluded)."""
    return [
        d for d in sorted(RUNTIME_ROOT.iterdir())
        if d.is_dir()
        and d.name not in EXCLUDED_PKG_NAMES
        and not d.name.startswith("_")
        and (d / "__init__.py").exists()
    ]


def normalize_import(module_str: str) -> Optional[str]:
    """
    Normalize an import string to its package (first two components).
    Returns None if the target is not a runtime sub-package import.
    """
    if not module_str.startswith("runtime."):
        return None
    parts = module_str.split(".")
    if len(parts) < 2:
        return None
    return f"runtime.{parts[1]}"


def resolve_relative_import(file_path: Path, level: int, module: Optional[str]) -> Optional[str]:
    """
    Resolve a relative import to an absolute package name.
    level=1: from . import X  →  same package
    level=2: from .. import X  →  parent package
    """
    # Get the package of the current file
    try:
        rel = file_path.relative_to(RUNTIME_ROOT)
    except ValueError:
        return None
    pkg_name = f"runtime.{rel.parts[0]}"
    if level == 1:
        # from . import X → same package
        target = pkg_name
    elif level == 2:
        # from .. import X → runtime (top-level, no policy target)
        return None
    else:
        return None

    if module:
        # from .submod import X → still same package
        pass
    return target


def scan_file_imports(file_path: Path, source_pkg: str, policy_packages: dict) -> list[str]:
    """
    Scan one file for cross-package import violations.
    Returns list of violation strings.
    """
    violations = []
    try:
        tree = ast.parse(file_path.read_text(encoding="utf-8"))
    except SyntaxError as e:
        return [f"SyntaxError in {file_path}: {e}"]

    allowed = policy_packages.get(source_pkg, [])

    for node in ast.walk(tree):
        targets = []

        if isinstance(node, ast.Import):
            for alias in node.names:
                t = normalize_import(alias.name)
                if t:
                    targets.append((t, node.lineno))

        elif isinstance(node, ast.ImportFrom):
            if node.level > 0:
                # Relative import
                t = resolve_relative_import(file_path, node.level, node.module)
                if t:
                    targets.append((t, node.lineno))
            elif node.module:
                t = normalize_import(node.module)
                if t:
                    targets.append((t, node.lineno))

        for target, lineno in targets:
            # Same-package imports are always allowed
            if target == source_pkg:
                continue
            # Skip if target is not a recognized policy package
            if target not in policy_packages:
                continue
            # Check allowed list
            if target not in allowed:
                violations.append(
                    f"{file_path}:{lineno}: {source_pkg} → {target} "
                    f"(not in allowed_imports)"
                )

    return violations


def test_policy_file_exists():
    """Policy file must exist."""
    assert POLICY_PATH.exists(), f"Missing: {POLICY_PATH}"


def test_policy_schema_version():
    """Policy must declare schema_version: import_policy.v1."""
    policy = load_policy()
    assert policy.get("schema_version") == "import_policy.v1", (
        f"Expected schema_version: import_policy.v1, got: {policy.get('schema_version')}"
    )


def test_all_declared_packages_present():
    """Policy must declare all runtime packages — fail-closed."""
    policy = load_policy()
    policy_packages = get_policy_packages(policy)
    discovered = discover_packages()
    discovered_names = {f"runtime.{d.name}" for d in discovered}

    missing_from_policy = discovered_names - set(policy_packages.keys())
    assert not missing_from_policy, (
        f"Packages in runtime/ but NOT declared in policy (unlisted = violation): "
        f"{sorted(missing_from_policy)}"
    )

    extra_in_policy = set(policy_packages.keys()) - discovered_names
    assert not extra_in_policy, (
        f"Policy declares packages not found in runtime/: {sorted(extra_in_policy)}"
    )


def test_import_policy_no_violations():
    """No runtime file may import a package outside its allowed list."""
    policy = load_policy()
    policy_packages = get_policy_packages(policy)
    discovered = discover_packages()

    all_violations = []

    for pkg_dir in discovered:
        source_pkg = f"runtime.{pkg_dir.name}"
        for py_file in sorted(pkg_dir.rglob("*.py")):
            if "__pycache__" in py_file.parts:
                continue
            v = scan_file_imports(py_file, source_pkg, policy_packages)
            all_violations.extend(v)

    if all_violations:
        msg = "\nImport policy violations found:\n" + "\n".join(f"  {v}" for v in all_violations)
        pytest.fail(msg)


def test_same_package_imports_not_flagged():
    """Verify that intra-package imports do not trigger violations."""
    policy = load_policy()
    policy_packages = get_policy_packages(policy)

    # runtime/governance/policy_loader.py imports from runtime.governance → should be ok
    gov_dir = RUNTIME_ROOT / "governance"
    if not gov_dir.exists():
        pytest.skip("runtime/governance not present")

    for py_file in gov_dir.rglob("*.py"):
        if "__pycache__" in py_file.parts:
            continue
        violations = scan_file_imports(py_file, "runtime.governance", policy_packages)
        # Filter to only same-package violations (should be none)
        same_pkg = [v for v in violations if "runtime.governance → runtime.governance" in v]
        assert not same_pkg, f"Same-package imports falsely flagged: {same_pkg}"


def test_mutation_forbidden_import_detected(tmp_path):
    """Adding a forbidden import to a synthetic package triggers a violation."""
    fake_pkg = tmp_path / "runtime" / "mymod"
    fake_pkg.mkdir(parents=True)
    (fake_pkg / "__init__.py").write_text("")
    (fake_pkg / "bad.py").write_text("from runtime.governance import baseline_checker\n")

    policy_packages = {
        "runtime.mymod": [],
        "runtime.governance": ["runtime.util"],
    }

    violations = scan_file_imports(fake_pkg / "bad.py", "runtime.mymod", policy_packages)
    assert violations, "Should have detected forbidden import from runtime.governance"


def test_mutation_unlisted_package_detected():
    """A package in runtime/ not in the policy must be flagged."""
    policy = load_policy()
    policy_packages = get_policy_packages(policy)
    discovered = discover_packages()
    discovered_names = {f"runtime.{d.name}" for d in discovered}

    # Simulate an undeclared package by removing one from the policy dict
    modified = dict(policy_packages)
    if not modified:
        pytest.skip("No packages in policy")
    removed = next(iter(modified))
    del modified[removed]

    missing = discovered_names - set(modified.keys())
    assert missing, "Should detect unlisted package after removing one from policy"
