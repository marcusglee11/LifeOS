#!/usr/bin/env python3
"""
Build Bundle for Build Loop Phase 1a.

Creates a deterministic, portable bundle ZIP and runs the audit gate.
Exit codes:
  0 = SUCCESS (bundle built and gate passed)
  1 = BUILD ERROR
  2 = GATE FAIL
  3 = GATE BLOCKED

Usage:
  python scripts/build_bundle_build_loop_phase1a.py [--output-dir PATH]
"""

import argparse
import hashlib
import os
import subprocess
import sys
import zipfile
from pathlib import Path


# Bundle configuration
BUNDLE_NAME = "Bundle_Build_Loop_Phase1a_v1.0.zip"
MANIFEST_NAME = "manifest_phase1a_v1.0.txt"

# Files to include (repo-relative paths)
INCLUDE_FILES = [
    # Scripts (audit gate + bundle builder)
    "scripts/audit_gate_build_loop_phase1a.py",
    "scripts/build_bundle_build_loop_phase1a.py",
    # Implementation plan
    "implementation_plan.md",
    # Governance/spec
    "docs/01_governance/Council_Ruling_Build_Loop_Architecture_v1.0.md",
    "docs/03_runtime/LifeOS_Autonomous_Build_Loop_Architecture_v0.3.md",
    "docs/LifeOS_Autonomous_Build_Loop_Architecture_v0.3.md",
    "docs/INDEX.md",
    # Runtime agents
    "runtime/agents/__init__.py",
    "runtime/agents/api.py",
    "runtime/agents/logging.py",
    "runtime/agents/agent_logging.py",
    "runtime/agents/fixtures.py",
    # Runtime orchestration
    "runtime/orchestration/run_controller.py",
    # Runtime governance
    "runtime/governance/__init__.py",
    "runtime/governance/baseline_checker.py",
    # Tests
    "runtime/tests/test_run_controller.py",
    "runtime/tests/test_agent_api.py",
    "runtime/tests/test_baseline_governance.py",
]

# Exclude patterns
EXCLUDE_PATTERNS = [
    "__pycache__",
    ".pyc",
    ".pyo",
    "Thumbs.db",
    ".DS_Store",
]


def compute_sha256(path: Path) -> str:
    """Compute SHA256 hash of a file."""
    hasher = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def should_exclude(path: str) -> bool:
    """Check if path matches any exclude pattern."""
    for pattern in EXCLUDE_PATTERNS:
        if pattern in path:
            return True
    return False


def build_bundle(repo_root: Path, output_dir: Path) -> tuple[Path, Path]:
    """
    Build the bundle ZIP and manifest.
    
    Returns (zip_path, manifest_path).
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    
    zip_path = output_dir / BUNDLE_NAME
    manifest_path = output_dir / MANIFEST_NAME
    
    print(f"Building bundle: {zip_path}")
    print(f"Repo root: {repo_root}")
    print()
    
    # Collect files
    files_to_include = []
    missing_files = []
    
    for rel_path in sorted(INCLUDE_FILES):
        full_path = repo_root / rel_path
        if full_path.exists():
            if not should_exclude(rel_path):
                files_to_include.append((rel_path, full_path))
        else:
            missing_files.append(rel_path)
    
    if missing_files:
        print("WARNING: Missing files (will be skipped):")
        for f in missing_files:
            print(f"  - {f}")
        print()
    
    # Build manifest
    manifest_lines = []
    for rel_path, full_path in files_to_include:
        sha256 = compute_sha256(full_path)
        manifest_lines.append(f"{sha256}  {rel_path}")
    
    manifest_content = "\n".join(manifest_lines) + "\n"
    manifest_path.write_text(manifest_content, encoding="utf-8")
    print(f"Manifest written: {manifest_path}")
    
    # Build ZIP with forward-slash paths
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for rel_path, full_path in files_to_include:
            # Ensure forward slashes for portability
            arc_name = rel_path.replace("\\", "/")
            zf.write(full_path, arc_name)
            print(f"  Added: {arc_name}")
        
        # Include manifest in ZIP
        zf.writestr("manifest.txt", manifest_content)
        print(f"  Added: manifest.txt")
    
    print()
    print(f"Bundle created: {zip_path}")
    print(f"Total files: {len(files_to_include) + 1}")
    
    return zip_path, manifest_path


def run_audit_gate(zip_path: Path, repo_root: Path) -> int:
    """
    Run the audit gate on the bundle.
    
    Returns exit code from the gate.
    """
    gate_script = repo_root / "scripts" / "audit_gate_build_loop_phase1a.py"
    
    if not gate_script.exists():
        print(f"ERROR: Audit gate script not found: {gate_script}")
        return 3  # BLOCKED
    
    print()
    print("=" * 60)
    print("Running Audit Gate...")
    print("=" * 60)
    
    result = subprocess.run(
        [sys.executable, str(gate_script), "--zip", str(zip_path)],
        cwd=repo_root,
    )
    
    return result.returncode


def main():
    parser = argparse.ArgumentParser(description="Build Bundle for Build Loop Phase 1a")
    parser.add_argument(
        "--output-dir",
        default="artifacts/bundles",
        help="Output directory for bundle (default: artifacts/bundles)",
    )
    args = parser.parse_args()
    
    # Determine repo root (script is in scripts/)
    script_path = Path(__file__).resolve()
    repo_root = script_path.parent.parent
    
    output_dir = repo_root / args.output_dir
    
    # Build the bundle
    try:
        zip_path, manifest_path = build_bundle(repo_root, output_dir)
    except Exception as e:
        print(f"BUILD ERROR: {e}")
        sys.exit(1)
    
    # Run audit gate
    gate_exit = run_audit_gate(zip_path, repo_root)
    
    if gate_exit == 0:
        print()
        print("=" * 60)
        print("SUCCESS: Bundle built and audit gate PASSED")
        print(f"  ZIP: {zip_path}")
        print(f"  Manifest: {manifest_path}")
        print("=" * 60)
        sys.exit(0)
    elif gate_exit == 2:
        print()
        print("=" * 60)
        print("FAIL: Audit gate failed. Bundle is NOT deliverable.")
        print("=" * 60)
        sys.exit(2)
    else:
        print()
        print("=" * 60)
        print("BLOCKED: Audit gate could not complete.")
        print("=" * 60)
        sys.exit(3)


if __name__ == "__main__":
    main()
