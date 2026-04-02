#!/usr/bin/env python3
"""Generate .context/REPO_MAP.md — a deterministic, commit-stamped repo map.

Pure-function core with a thin CLI wrapper.  No runtime module imports;
scans the tree using only stdlib (ast, pathlib, subprocess, yaml).
"""

from __future__ import annotations

import argparse
import ast
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

GENERATOR_VERSION = "1.0"
DEFAULT_OUTPUT = ".context/REPO_MAP.md"
DEFAULT_OVERRIDES = "scripts/repo_map_overrides.yaml"

EXCLUDE_DIRS = frozenset({
    "__pycache__", ".git", "node_modules", ".mypy_cache",
    ".pytest_cache", ".tox", ".venv", "venv", ".eggs",
})

# Top-level dirs that are always excluded from the scan
TOP_LEVEL_EXCLUDE = frozenset({
    "__pycache__", ".git", ".github", ".worktrees", ".context",
    ".claude", "node_modules", ".mypy_cache", ".pytest_cache",
})

# Key files cap per module
KEY_FILES_CAP = 5
GIT_STATUS_TIMEOUTS_S = (10, 30)


# ---------------------------------------------------------------------------
# YAML loader (minimal, avoids pyyaml dependency issues)
# ---------------------------------------------------------------------------

def _load_yaml_simple(path: Path) -> dict:
    """Load a simple YAML file.  Falls back to empty dict on any error."""
    try:
        import yaml  # type: ignore[import-untyped]
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception:
        return {}


# ---------------------------------------------------------------------------
# Git helpers
# ---------------------------------------------------------------------------

def get_head_ref(repo: Path) -> str:
    """Return HEAD commit short sha."""
    try:
        result = subprocess.run(
            ["git", "-C", str(repo), "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, timeout=10,
        )
        return result.stdout.strip() if result.returncode == 0 else "UNKNOWN"
    except Exception:
        return "UNKNOWN"


def is_tree_dirty(repo: Path) -> bool:
    """Return True if working tree has uncommitted changes."""
    for timeout_s in GIT_STATUS_TIMEOUTS_S:
        try:
            result = subprocess.run(
                ["git", "-C", str(repo), "status", "--porcelain=v1", "--untracked-files=no"],
                capture_output=True,
                text=True,
                timeout=timeout_s,
            )
        except subprocess.TimeoutExpired:
            continue
        except Exception:
            return True
        return result.returncode != 0 or bool(result.stdout.strip())
    return True


# ---------------------------------------------------------------------------
# AST helpers
# ---------------------------------------------------------------------------

_BOILERPLATE_RE_PATTERN = r"^runtime\.\w+ package$"

def _is_boilerplate_docstring(doc: str) -> bool:
    """Return True if the docstring is auto-generated boilerplate."""
    first_line = doc.strip().split("\n")[0].strip().rstrip(".")
    return bool(re.match(_BOILERPLATE_RE_PATTERN, first_line))


def _extract_docstring(path: Path) -> str | None:
    """Extract the module-level docstring from a Python file via AST."""
    try:
        source = path.read_text(encoding="utf-8", errors="replace")
        tree = ast.parse(source, filename=str(path))
        return ast.get_docstring(tree)
    except Exception:
        return None


def _extract_imports(path: Path) -> set[str]:
    """Extract top-level import targets from a Python file.

    Returns a set of top-level package names (e.g. ``{"runtime.governance"}``
    from ``from runtime.governance.core import ...``).
    """
    results: set[str] = set()
    try:
        source = path.read_text(encoding="utf-8", errors="replace")
        tree = ast.parse(source, filename=str(path))
    except Exception:
        return results

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                results.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                results.add(node.module)
    return results


def _resolve_runtime_package(import_path: str) -> str | None:
    """Map an import path to its runtime top-level package, or None."""
    parts = import_path.split(".")
    if len(parts) >= 2 and parts[0] == "runtime":
        return f"runtime.{parts[1]}"
    return None


# ---------------------------------------------------------------------------
# Scanners
# ---------------------------------------------------------------------------

def _count_lines(path: Path) -> int:
    """Count physical lines in a file."""
    try:
        return len(path.read_bytes().split(b"\n"))
    except Exception:
        return 0


def _is_excluded(p: Path) -> bool:
    return any(part in EXCLUDE_DIRS for part in p.parts)


def scan_top_level_dirs(repo: Path, overrides: dict[str, str]) -> list[dict[str, str]]:
    """Scan top-level directories and return name + purpose."""
    results = []
    for entry in sorted(repo.iterdir()):
        if not entry.is_dir():
            continue
        name = entry.name
        if name in TOP_LEVEL_EXCLUDE or name.startswith("."):
            continue

        # Purpose precedence: override > known defaults > UNSPECIFIED
        if name in overrides:
            purpose = overrides[name]
        else:
            purpose = _KNOWN_TOP_LEVEL.get(name, "UNSPECIFIED")
        results.append({"name": name, "purpose": purpose})
    return results


_KNOWN_TOP_LEVEL: dict[str, str] = {
    "artifacts": "Agent-generated outputs, plans, handoffs, evidence",
    "case_studies": "Case study documentation",
    "config": "Configuration files (agent roles, governance, tasks)",
    "demo_env": "Demo environment setup",
    "doc_steward": "Document governance CLI",
    "docs": "Source of truth for governance, specs, and protocols",
    "logs": "Runtime logs",
    "opencode_governance": "OpenCode governance integration",
    "project_builder": "Multi-agent orchestration",
    "protocols": "Protocol definitions",
    "recursive_kernel": "Self-improvement loop and backlog parser",
    "runtime": "COO Runtime — main codebase (FSM, orchestration, governance)",
    "runtime_state": "Runtime state snapshots",
    "schemas": "Schema definitions",
    "scripts": "Utility and workflow scripts",
    "session_logs": "Legacy session logs",
    "spikes": "Spike/experimental work",
    "tests": "Top-level integration tests",
    "tests_doc": "Documentation compliance tests",
    "tests_recursive": "Recursive kernel tests",
    "tools": "Standalone tool scripts",
}


def scan_runtime_packages(
    repo: Path,
    overrides: dict[str, str],
) -> list[dict[str, Any]]:
    """Scan runtime/ sub-packages and return inventory."""
    runtime_dir = repo / "runtime"
    if not runtime_dir.is_dir():
        return []

    packages = []
    for entry in sorted(runtime_dir.iterdir()):
        if not entry.is_dir():
            continue
        name = entry.name
        if name in EXCLUDE_DIRS or name.startswith("."):
            continue

        init_py = entry / "__init__.py"
        if not init_py.exists():
            continue

        # Purpose precedence: override > __init__.py docstring > dominant > UNDOCUMENTED
        override_key = f"runtime/{name}"
        if override_key in overrides:
            purpose = overrides[override_key]
        else:
            docstring = _extract_docstring(init_py)
            if docstring and not _is_boilerplate_docstring(docstring):
                purpose = docstring.strip().split("\n")[0].strip().rstrip(".")
            else:
                purpose = _find_dominant_module_purpose(entry)

        # Key files
        py_files = sorted(
            f for f in entry.rglob("*.py")
            if not _is_excluded(f) and f.name != "__init__.py"
        )
        key_files = [str(f.relative_to(repo)) for f in py_files[:KEY_FILES_CAP]]

        # Stats
        all_py = [f for f in entry.rglob("*.py") if not _is_excluded(f)]
        file_count = len(all_py)
        line_count = sum(_count_lines(f) for f in all_py)

        packages.append({
            "name": name,
            "purpose": purpose,
            "key_files": key_files,
            "file_count": file_count,
            "line_count": line_count,
        })

    return packages


def _find_dominant_module_purpose(pkg_dir: Path) -> str:
    """Try to find a clearly authoritative docstring from the largest module."""
    py_files = sorted(
        (f for f in pkg_dir.glob("*.py") if f.name != "__init__.py" and not _is_excluded(f)),
        key=lambda f: f.stat().st_size,
        reverse=True,
    )
    for f in py_files[:3]:
        doc = _extract_docstring(f)
        if doc and len(doc.strip()) > 10:
            return doc.strip().split("\n")[0].strip().rstrip(".")
    return "UNDOCUMENTED"


def scan_source_test_mapping(
    repo: Path,
    packages: list[dict[str, Any]],
) -> list[dict[str, str]]:
    """Derive source-to-test mappings backed by existing test paths."""
    mappings = []
    tests_dir = repo / "runtime" / "tests"

    for pkg in packages:
        name = pkg["name"]
        if name == "tests":
            continue

        # Check runtime/tests/<name>/ directory
        test_pkg_dir = tests_dir / name
        if test_pkg_dir.is_dir():
            mappings.append({
                "source": f"runtime/{name}/",
                "tests": f"runtime/tests/{name}/",
            })
            continue

        # Check runtime/tests/test_<name>*.py files
        test_files = sorted(tests_dir.glob(f"test_{name}*.py"))
        if test_files:
            targets = " ".join(str(f.relative_to(repo)) for f in test_files[:3])
            mappings.append({
                "source": f"runtime/{name}/",
                "tests": targets,
            })

    return mappings


def scan_dependency_edges(repo: Path, packages: list[dict[str, Any]]) -> list[tuple[str, str]]:
    """Scan all runtime Python files for internal cross-package imports.

    Returns sorted, deduplicated list of (from_pkg, to_pkg) edges.
    """
    edges: set[tuple[str, str]] = set()
    runtime_dir = repo / "runtime"
    pkg_names = {f"runtime.{p['name']}" for p in packages if p["name"] != "tests"}

    for pkg in packages:
        if pkg["name"] == "tests":
            continue
        pkg_dir = runtime_dir / pkg["name"]
        from_pkg = f"runtime.{pkg['name']}"

        for py_file in pkg_dir.rglob("*.py"):
            if _is_excluded(py_file):
                continue
            imports = _extract_imports(py_file)
            for imp in imports:
                to_pkg = _resolve_runtime_package(imp)
                if to_pkg and to_pkg != from_pkg and to_pkg in pkg_names:
                    edges.add((from_pkg, to_pkg))

    return sorted(edges)


def scan_entry_points(repo: Path) -> list[dict[str, str]]:
    """Detect CLI entry points and main scripts."""
    entries = []

    # pyproject.toml [project.scripts]
    pyproject = repo / "pyproject.toml"
    if pyproject.exists():
        try:
            content = pyproject.read_text(encoding="utf-8")
            in_scripts = False
            for line in content.split("\n"):
                stripped = line.strip()
                if stripped == "[project.scripts]":
                    in_scripts = True
                    continue
                if in_scripts:
                    if stripped.startswith("["):
                        break
                    if "=" in stripped:
                        name, target = stripped.split("=", 1)
                        entries.append({
                            "name": name.strip().strip('"'),
                            "target": target.strip().strip('"'),
                            "type": "cli",
                        })
        except Exception:
            pass

    # Main scripts in scripts/ (list workflow/ subdirectory + count top-level)
    scripts_dir = repo / "scripts"
    if scripts_dir.is_dir():
        # Workflow scripts (always listed — high-value)
        workflow_dir = scripts_dir / "workflow"
        if workflow_dir.is_dir():
            for f in sorted(workflow_dir.glob("*.py")):
                if f.name.startswith("_"):
                    continue
                entries.append({
                    "name": f.name,
                    "target": f"scripts/workflow/{f.name}",
                    "type": "script",
                })

        # Top-level scripts: count only, too many to list
        top_scripts = sorted(f for f in scripts_dir.glob("*.py") if not f.name.startswith("_"))
        if top_scripts:
            entries.append({
                "name": f"({len(top_scripts)} top-level scripts in scripts/)",
                "target": "scripts/",
                "type": "script_count",
            })

    return entries


def compute_stats(packages: list[dict[str, Any]]) -> dict[str, Any]:
    """Compute aggregate stats from scanned packages (excludes tests package)."""
    non_test = [p for p in packages if p["name"] != "tests"]
    total_files = sum(p["file_count"] for p in non_test)
    total_lines = sum(p["line_count"] for p in non_test)
    return {
        "total_packages": len(non_test),
        "total_files": total_files,
        "total_lines": total_lines,
    }


# ---------------------------------------------------------------------------
# Renderer
# ---------------------------------------------------------------------------

def render_repo_map(
    *,
    repo: Path,
    head_ref: str,
    tree_dirty: bool,
    generated_at: str,
    top_level: list[dict[str, str]],
    packages: list[dict[str, Any]],
    test_mappings: list[dict[str, str]],
    dep_edges: list[tuple[str, str]],
    entry_points: list[dict[str, str]],
    stats: dict[str, Any],
) -> str:
    """Render the repo map as markdown."""
    lines: list[str] = []

    # Header
    lines.append("# LifeOS Repo Map")
    lines.append("")
    lines.append("<!-- Auto-generated by scripts/generate_repo_map.py — do not hand-edit -->")
    lines.append("")
    lines.append("```")
    lines.append(f"generator_version: {GENERATOR_VERSION}")
    lines.append(f"generated_from_ref: {head_ref}")
    lines.append(f"working_tree_dirty: {str(tree_dirty).lower()}")
    lines.append(f"generated_at: {generated_at}")
    lines.append("scan_scope: runtime/, top-level dirs, scripts/")
    lines.append(f"exclusions: {', '.join(sorted(EXCLUDE_DIRS))}")
    lines.append("```")
    lines.append("")

    # Section 1: Top-level structure
    lines.append("## Top-Level Structure")
    lines.append("")
    for entry in top_level:
        lines.append(f"- **{entry['name']}/** — {entry['purpose']}")
    lines.append("")

    # Section 2: Runtime module inventory
    lines.append("## Runtime Module Inventory")
    lines.append("")
    for pkg in packages:
        if pkg["name"] == "tests":
            continue
        lines.append(f"### runtime/{pkg['name']}/")
        lines.append(f"- Purpose: {pkg['purpose']}")
        lines.append(f"- Files: {pkg['file_count']} | Lines: {pkg['line_count']}")
        if pkg["key_files"]:
            lines.append(f"- Key: {', '.join(pkg['key_files'])}")
        lines.append("")

    # Section 3: Source-to-test mapping
    lines.append("## Source → Test Mapping")
    lines.append("")
    for m in test_mappings:
        lines.append(f"- `{m['source']}` → `{m['tests']}`")
    lines.append("")

    # Section 4: Dependency edges
    lines.append("## Internal Dependency Edges")
    lines.append("")
    if dep_edges:
        for from_pkg, to_pkg in dep_edges:
            lines.append(f"- {from_pkg} → {to_pkg}")
    else:
        lines.append("- (none detected)")
    lines.append("")

    # Section 5: Entry points
    lines.append("## Entry Points")
    lines.append("")
    cli_entries = [e for e in entry_points if e["type"] == "cli"]
    script_entries = [e for e in entry_points if e["type"] == "script"]
    count_entries = [e for e in entry_points if e["type"] == "script_count"]
    if cli_entries:
        lines.append("### CLI Commands")
        for e in cli_entries:
            lines.append(f"- `{e['name']}` → {e['target']}")
        lines.append("")
    if script_entries or count_entries:
        lines.append("### Scripts")
        for e in script_entries:
            lines.append(f"- `{e['target']}`")
        for e in count_entries:
            lines.append(f"- {e['name']}")
        lines.append("")

    # Section 6: Stats
    lines.append("## Stats")
    lines.append("")
    lines.append(f"- Runtime packages: {stats['total_packages']}")
    lines.append(f"- Runtime Python files: {stats['total_files']}")
    lines.append(f"- Runtime lines of code: {stats['total_lines']}")
    lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Orchestrator (pure function)
# ---------------------------------------------------------------------------

def generate_repo_map(
    repo: Path,
    *,
    generated_at: str | None = None,
    overrides_path: Path | None = None,
) -> str:
    """Generate the full repo map content.

    Parameters
    ----------
    repo : Path
        Repository root.
    generated_at : str or None
        ISO timestamp to embed.  If None, uses current UTC time.
    overrides_path : Path or None
        Path to repo_map_overrides.yaml.  If None, uses default location.
    """
    if generated_at is None:
        generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    if overrides_path is None:
        overrides_path = repo / DEFAULT_OVERRIDES

    raw_overrides = _load_yaml_simple(overrides_path)
    overrides = raw_overrides.get("overrides", {}) or {}

    head_ref = get_head_ref(repo)
    tree_dirty = is_tree_dirty(repo)
    top_level = scan_top_level_dirs(repo, overrides)
    packages = scan_runtime_packages(repo, overrides)
    test_mappings = scan_source_test_mapping(repo, packages)
    dep_edges = scan_dependency_edges(repo, packages)
    entry_points = scan_entry_points(repo)
    stats = compute_stats(packages)

    return render_repo_map(
        repo=repo,
        head_ref=head_ref,
        tree_dirty=tree_dirty,
        generated_at=generated_at,
        top_level=top_level,
        packages=packages,
        test_mappings=test_mappings,
        dep_edges=dep_edges,
        entry_points=entry_points,
        stats=stats,
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo-root", default=".",
        help="Repository root (default: current directory).",
    )
    parser.add_argument(
        "--output", default=None,
        help=f"Output path (default: <repo>/{DEFAULT_OUTPUT}).",
    )
    parser.add_argument(
        "--overrides", default=None,
        help=f"Overrides YAML path (default: <repo>/{DEFAULT_OVERRIDES}).",
    )
    args = parser.parse_args()

    repo = Path(args.repo_root).resolve()
    output = Path(args.output) if args.output else repo / DEFAULT_OUTPUT
    overrides_path = Path(args.overrides) if args.overrides else None

    output.parent.mkdir(parents=True, exist_ok=True)
    content = generate_repo_map(repo, overrides_path=overrides_path)
    output.write_text(content, encoding="utf-8")

    line_count = content.count("\n")
    print(f"Wrote {output} ({line_count} lines)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
