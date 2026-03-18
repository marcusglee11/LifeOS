#!/usr/bin/env python3
"""
Entropy Scanner v1 — Bounded codebase decay detection.

Detectors (v1):
  1. stale_repo_map     — REPO_MAP.md vs current HEAD commit count
  2. unused_init_exports — runtime/*/__init__.py exports not imported anywhere
  3. doc_path_references — LIFEOS_STATE.md + BACKLOG.md path refs that don't exist
  4. stale_canonical_state — canonical_state.yaml older than LIFEOS_STATE.md

Usage:
  python scripts/entropy/scan_v1.py [--output artifacts/entropy/scan_YYYYMMDD.json]

Exits 0 if report generated successfully. Exits 1 if the scanner itself is broken.
Reports are NOT committed automatically.
"""
import argparse
import ast
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent.parent
REPO_MAP_PATH = REPO_ROOT / ".context" / "REPO_MAP.md"
STATE_FILE = REPO_ROOT / "docs" / "11_admin" / "LIFEOS_STATE.md"
BACKLOG_FILE = REPO_ROOT / "docs" / "11_admin" / "BACKLOG.md"
CANONICAL_STATE_PATH = REPO_ROOT / "artifacts" / "status" / "canonical_state.yaml"
STALE_REPO_MAP_THRESHOLD = 5  # warn if REPO_MAP is >5 commits behind HEAD


def run_git(args: list, timeout: int = 10) -> str:
    """Run a git command from REPO_ROOT, return stdout or empty string on failure."""
    try:
        result = subprocess.run(
            ["git", "-C", str(REPO_ROOT)] + args,
            capture_output=True, text=True, timeout=timeout,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return ""


def current_head() -> str:
    return run_git(["rev-parse", "HEAD"]) or "unknown"


# ---------------------------------------------------------------------------
# Detector 1: Stale REPO_MAP
# ---------------------------------------------------------------------------

def detect_stale_repo_map() -> dict:
    """Warn if REPO_MAP.md is >5 commits behind HEAD."""
    if not REPO_MAP_PATH.exists():
        return {"status": "error", "detail": "REPO_MAP.md not found"}

    content = REPO_MAP_PATH.read_text(encoding="utf-8")
    m = re.search(r"generated_from_ref:\s*([0-9a-f]{7,40})", content)
    if not m:
        return {"status": "warn", "detail": "Could not parse generated_from_ref from REPO_MAP.md"}

    map_ref = m.group(1)
    head = current_head()
    if not head or head == "unknown":
        return {"status": "warn", "detail": "Could not determine HEAD commit"}

    # Count commits between map_ref and HEAD
    count_str = run_git(["rev-list", "--count", f"{map_ref}..HEAD"])
    if not count_str:
        return {"status": "warn", "detail": f"Could not count commits since {map_ref[:8]}"}

    try:
        count = int(count_str)
    except ValueError:
        return {"status": "warn", "detail": f"Unexpected rev-list output: {count_str!r}"}

    if count > STALE_REPO_MAP_THRESHOLD:
        return {
            "status": "warn",
            "detail": (
                f"REPO_MAP.md is {count} commits behind HEAD "
                f"(generated at {map_ref[:8]}, threshold={STALE_REPO_MAP_THRESHOLD})"
            ),
        }

    return {"status": "ok", "detail": f"REPO_MAP.md is {count} commit(s) behind HEAD"}


# ---------------------------------------------------------------------------
# Detector 2: Unused __init__ exports
# ---------------------------------------------------------------------------

def get_all_runtime_imports() -> set[str]:
    """Collect all names imported from runtime.* anywhere in runtime/ (excluding __init__.py)."""
    imported_names: set[str] = set()
    runtime = REPO_ROOT / "runtime"
    for py_file in runtime.rglob("*.py"):
        if "__pycache__" in py_file.parts:
            continue
        if py_file.name == "__init__.py":
            continue
        try:
            tree = ast.parse(py_file.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("runtime."):
                for alias in node.names:
                    imported_names.add(alias.name)
    return imported_names


def detect_unused_init_exports() -> dict:
    """Find names exported in runtime/*/__init__.py that are never imported elsewhere."""
    runtime = REPO_ROOT / "runtime"
    if not runtime.exists():
        return {"status": "error", "detail": "runtime/ not found", "findings": []}

    all_imports = get_all_runtime_imports()
    findings = []

    for pkg_dir in sorted(runtime.iterdir()):
        if not pkg_dir.is_dir():
            continue
        if pkg_dir.name.startswith("_") or pkg_dir.name in {"tests", "__pycache__", "memory", "spec"}:
            continue
        init_file = pkg_dir / "__init__.py"
        if not init_file.exists():
            continue

        try:
            tree = ast.parse(init_file.read_text(encoding="utf-8"))
        except SyntaxError:
            continue

        # Collect __all__ if defined, else top-level assigned names
        exported: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == "__all__":
                        if isinstance(node.value, ast.List):
                            for elt in node.value.elts:
                                if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                                    exported.append(elt.value)

        for name in exported:
            if name not in all_imports:
                findings.append(
                    f"runtime/{pkg_dir.name}/__init__.py exports '{name}' but it is never imported"
                )

    status = "warn" if findings else "ok"
    return {"status": status, "findings": findings}


# ---------------------------------------------------------------------------
# Detector 3: Doc path references
# ---------------------------------------------------------------------------

_PATH_PATTERN = re.compile(
    r"`([a-zA-Z0-9_./-]+\.[a-zA-Z]{2,6})`"   # backtick-quoted paths with extension
    r"|"
    r"(?<!\w)((?:[a-zA-Z0-9_-]+/)+[a-zA-Z0-9_.-]+\.[a-zA-Z]{2,6})(?!\w)"  # bare paths
)


def extract_path_refs(text: str) -> list[str]:
    """Extract file path references from markdown text."""
    paths = set()
    for m in _PATH_PATTERN.finditer(text):
        candidate = m.group(1) or m.group(2)
        if candidate and "/" in candidate:
            # Filter out obvious non-paths
            if not candidate.startswith("http") and ".." not in candidate:
                paths.add(candidate)
    return sorted(paths)


def detect_doc_path_references() -> dict:
    """Check LIFEOS_STATE.md and BACKLOG.md for path references that don't exist."""
    findings = []

    for doc_file in [STATE_FILE, BACKLOG_FILE]:
        if not doc_file.exists():
            findings.append(f"{doc_file.name}: file not found")
            continue
        content = doc_file.read_text(encoding="utf-8")
        refs = extract_path_refs(content)
        for ref in refs:
            full_path = REPO_ROOT / ref
            if not full_path.exists():
                findings.append(f"{doc_file.name}: references non-existent path '{ref}'")

    status = "warn" if findings else "ok"
    return {"status": status, "findings": findings}


# ---------------------------------------------------------------------------
# Detector 4: Stale canonical_state.yaml
# ---------------------------------------------------------------------------

def detect_stale_canonical_state() -> dict:
    """Warn if canonical_state.yaml is older than LIFEOS_STATE.md (git mtime comparison)."""
    if not CANONICAL_STATE_PATH.exists():
        return {"status": "ok", "detail": "canonical_state.yaml not present (not yet generated)"}

    if not STATE_FILE.exists():
        return {"status": "warn", "detail": "LIFEOS_STATE.md not found"}

    # Read extracted_at from canonical_state.yaml
    try:
        import yaml as _yaml
        with CANONICAL_STATE_PATH.open(encoding="utf-8") as f:
            canonical = _yaml.safe_load(f)
        extracted_at_str = canonical.get("extracted_at", "")
    except Exception as e:
        return {"status": "warn", "detail": f"Could not parse canonical_state.yaml: {e}"}

    if not extracted_at_str:
        return {"status": "warn", "detail": "canonical_state.yaml missing extracted_at field"}

    # Get last commit time of LIFEOS_STATE.md via git log
    state_commit_time_str = run_git([
        "log", "-1", "--format=%cI", "--", str(STATE_FILE.relative_to(REPO_ROOT))
    ])
    if not state_commit_time_str:
        return {"status": "warn", "detail": "Could not determine LIFEOS_STATE.md last commit time"}

    try:
        from datetime import datetime as _dt
        extracted_at = _dt.fromisoformat(extracted_at_str.replace("Z", "+00:00"))
        state_commit_time = _dt.fromisoformat(state_commit_time_str)
    except ValueError as e:
        return {"status": "warn", "detail": f"Timestamp parse error: {e}"}

    if state_commit_time > extracted_at:
        return {
            "status": "warn",
            "detail": (
                f"canonical_state.yaml is stale: "
                f"LIFEOS_STATE.md last committed at {state_commit_time_str}, "
                f"but canonical_state.yaml extracted at {extracted_at_str}. "
                "Re-run scripts/extract_canonical_state.py."
            ),
        }

    return {"status": "ok", "detail": "canonical_state.yaml is fresh"}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def build_report() -> dict:
    head = current_head()
    detectors = {
        "stale_repo_map": detect_stale_repo_map(),
        "unused_init_exports": detect_unused_init_exports(),
        "doc_path_references": detect_doc_path_references(),
        "stale_canonical_state": detect_stale_canonical_state(),
    }

    summary = {"ok": 0, "warn": 0, "error": 0}
    for result in detectors.values():
        status = result.get("status", "error")
        summary[status] = summary.get(status, 0) + 1

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "repo_ref": head,
        "scanner_version": "v1",
        "detectors": detectors,
        "summary": summary,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="LifeOS Entropy Scanner v1")
    parser.add_argument(
        "--output", "-o",
        default=None,
        help="Path to write JSON report (default: artifacts/entropy/scan_<date>.json)",
    )
    args = parser.parse_args()

    if args.output:
        output_path = Path(args.output)
    else:
        date_str = datetime.now().strftime("%Y%m%d")
        output_path = REPO_ROOT / "artifacts" / "entropy" / f"scan_{date_str}.json"

    try:
        report = build_report()
    except Exception as e:
        print(f"ERROR: Scanner failed: {e}", file=sys.stderr)
        return 1

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Report written to: {output_path}")

    # Print summary to stdout
    summary = report["summary"]
    print(f"Summary: ok={summary['ok']} warn={summary['warn']} error={summary['error']}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
