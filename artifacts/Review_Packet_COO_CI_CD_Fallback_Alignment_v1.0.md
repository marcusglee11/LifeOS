---
artifact_type: "REVIEW_PACKET"
schema_version: "1.0.0"
mission_ref: "Align CI/CD and regression tests with Copilot non-premium first fallback policy"
version: "1.0"
status: "PENDING_REVIEW"
---

# Review_Packet_COO_CI_CD_Fallback_Alignment_v1.0

## Scope Envelope

- Allowed: `.github/workflows/ci.yml`, `runtime/tools/openclaw_model_ladder_fix.py`, `runtime/tools/workflow_pack.py`, `runtime/tests/test_openclaw_policy_assert.py`, `runtime/tests/test_openclaw_memory_policy_assert.py`, `runtime/tests/test_openclaw_model_policy_assert.py`, `runtime/tests/test_workflow_pack.py`
- Forbidden observed: none

## Summary

Aligned CI/CD and policy test fixtures with the new subscription-first fallback rung `github-copilot/gpt-5-mini`.

Added a CI guard step to fail fast if legacy `github-copilot/claude-opus-4.6` reappears in OpenClaw policy/test sources. Updated closure test routing so changes to either OpenClaw policy assert tool run the full policy test bundle.

## Acceptance Mapping

- Policy test fixtures updated to new fallback rung: PASS
- Ladder repair baseline updated to new fallback rung: PASS
- Workflow targeted test routing expanded for policy bundle: PASS
- CI regression guard for legacy fallback string: PASS
- Targeted pytest validation of changed areas: PASS (32 passed)

## Evidence

- `pytest -q runtime/tests/test_openclaw_policy_assert.py runtime/tests/test_openclaw_memory_policy_assert.py runtime/tests/test_openclaw_model_policy_assert.py runtime/tests/test_workflow_pack.py`
  - Result: `32 passed`
- `rg -n "github-copilot/claude-opus-4.6|github-copilot/gpt-5-mini" ...`
  - Result: only expected guard reference for legacy id remains, active constants/fixtures use `gpt-5-mini`.

## Changed Files

- `.github/workflows/ci.yml`
- `runtime/tools/openclaw_model_ladder_fix.py`
- `runtime/tools/workflow_pack.py`
- `runtime/tests/test_openclaw_policy_assert.py`
- `runtime/tests/test_openclaw_memory_policy_assert.py`
- `runtime/tests/test_openclaw_model_policy_assert.py`
- `runtime/tests/test_workflow_pack.py`

## Appendix A — Flattened Code

### File: `.github/workflows/ci.yml`

````text
name: LifeOS CI

on:
  push:
    branches: [main, develop]
  pull_request:

jobs:
  test:
    name: Test Suite (Python ${{ matrix.python-version }})
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ['3.11', '3.12']
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
      
      - name: Set up Git config
        run: git config --global core.autocrlf false
      
      - name: Install dependencies
        run: |
          sudo apt-get update
          sudo apt-get install -y ripgrep
          sudo npm install -g markdownlint-cli
          pip install -r requirements-dev.txt

      - name: Enforce OpenClaw fallback policy constants
        run: |
          set -euo pipefail
          if rg -n "github-copilot/claude-opus-4.6" \
            runtime/tools/openclaw_policy_assert.py \
            runtime/tools/openclaw_model_policy_assert.py \
            runtime/tools/openclaw_model_ladder_fix.py \
            runtime/tests/test_openclaw_policy_assert.py \
            runtime/tests/test_openclaw_memory_policy_assert.py \
            runtime/tests/test_openclaw_model_policy_assert.py; then
            echo "::error::Legacy fallback github-copilot/claude-opus-4.6 detected in OpenClaw policy/test sources."
            exit 1
          fi

      - name: Run tests
        run: pytest -v --tb=short
        env:
          PYTHONPATH: ${{ github.workspace }}

      - name: Enforce Mission CLI Invariants
        run: |
          pytest -v runtime/tests/orchestration/test_validation_orchestrator.py
          pytest -v runtime/tests/test_cli_mission.py
        env:
          PYTHONPATH: ${{ github.workspace }}

  lint:
    name: Lint Check
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'
      
      - name: Run Biome linter
        run: npx @biomejs/biome check .
        continue-on-error: true  # Don't fail build on lint warnings initially

  docs:
    name: Documentation Validation
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          sudo apt-get update
          sudo apt-get install -y ripgrep
          pip install -r requirements-dev.txt

      - name: Run doc link validator
        if: github.event_name == 'pull_request'
        run: pytest tests_doc/test_links.py -v
        continue-on-error: true  # Report but don't block initially

      - name: DAP validation
        run: python -m doc_steward.cli dap-validate .
        env:
          PYTHONPATH: ${{ github.workspace }}

      - name: Doc freshness check (warn until 2026-02-26, then block)
        run: python -m doc_steward.cli freshness-check .
        env:
          PYTHONPATH: ${{ github.workspace }}
          LIFEOS_DOC_FRESHNESS_MODE: warn

  validate:
    name: Validate Artefact Index
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: pip install pyyaml
      
      - name: Run governance index validator
        run: |
          if [ -f tools/validate_governance_index.py ]; then
            python tools/validate_governance_index.py --repo-root .
          else
            echo "Validator not found, skipping"
          fi
        continue-on-error: true

      - name: Run Canon Spine validator
        run: |
          if [ ! -f scripts/validate_canon_spine.py ]; then
            echo "CRITICAL: scripts/validate_canon_spine.py missing!"
            exit 1
          fi
          python scripts/validate_canon_spine.py

````

### File: `runtime/tools/openclaw_model_ladder_fix.py`

````text
#!/usr/bin/env python3
"""
Safe repair tool for OpenClaw model ladder configuration.
Creates backup, applies minimal fixes, generates audit capsule.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple


EXECUTION_BASE = [
    "openai-codex/gpt-5.3-codex",
    "github-copilot/gpt-5-mini",
    "google-gemini-cli/gemini-3-flash-preview",
]
THINKING_BASE = list(EXECUTION_BASE)


def sha256_file(path: Path) -> str:
    """Compute SHA256 hash of a file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def apply_ladder_fixes(cfg: Dict[str, Any]) -> Tuple[Dict[str, Any], List[str]]:
    """
    Apply minimal fixes to config to satisfy ladder policy.
    Returns (fixed_config, changes_made).
    """
    changes: List[str] = []

    # Ensure agents.list exists
    if "agents" not in cfg:
        cfg["agents"] = {}
        changes.append("Created agents section")

    if "list" not in cfg["agents"]:
        cfg["agents"]["list"] = []
        changes.append("Created agents.list array")

    agents_list = cfg["agents"]["list"]

    # Helper to find or create an agent
    def ensure_agent(agent_id: str, ladder_base: List[str]) -> None:
        for agent in agents_list:
            if isinstance(agent, dict) and agent.get("id") == agent_id:
                # Agent exists, update its ladder if invalid
                model = agent.get("model", {})
                if not isinstance(model, dict):
                    agent["model"] = {}
                    model = agent["model"]
                    changes.append(f"{agent_id}: created model section")

                primary = model.get("primary")
                fallbacks = model.get("fallbacks", [])

                if primary != ladder_base[0]:
                    model["primary"] = ladder_base[0]
                    changes.append(f"{agent_id}: set primary to {ladder_base[0]}")

                if not isinstance(fallbacks, list):
                    fallbacks = []

                required_prefix = ladder_base[1:]
                existing = [str(x) for x in fallbacks if isinstance(x, str) and str(x).strip()]
                filtered_existing = [
                    x
                    for x in existing
                    if ("haiku" not in x.lower()) and ("small" not in x.lower()) and (not x.lower().startswith("claude-max/"))
                ]
                extras = [x for x in filtered_existing if x not in required_prefix]
                normalized_fallbacks = required_prefix + extras
                if existing != normalized_fallbacks:
                    model["fallbacks"] = normalized_fallbacks
                    changes.append(f"{agent_id}: normalized fallback prefix to subscription-first ladder")

                return

        # Agent doesn't exist, create it
        new_agent: Dict[str, Any] = {
            "id": agent_id,
            "model": {
                "primary": ladder_base[0],
                "fallbacks": ladder_base[1:],
            }
        }
        if agent_id == "think":
            new_agent["thinking"] = "extra_high"

        agents_list.append(new_agent)
        changes.append(f"{agent_id}: created agent with policy ladder")

    ensure_agent("main", EXECUTION_BASE)
    ensure_agent("quick", EXECUTION_BASE)
    ensure_agent("think", THINKING_BASE)

    return cfg, changes


def main() -> int:
    parser = argparse.ArgumentParser(description="Safe repair tool for OpenClaw model ladder configuration.")
    parser.add_argument("--config", default=str(Path.home() / ".openclaw" / "openclaw.json"))
    parser.add_argument("--dry-run", action="store_true", help="Show what would be changed without applying")
    args = parser.parse_args()

    config_path = Path(args.config).expanduser()

    if not config_path.exists():
        print(f"ERROR: Config file not found: {config_path}", file=sys.stderr)
        print(f"NEXT: Run 'openclaw onboard' to initialize configuration", file=sys.stderr)
        return 1

    print("=== OpenClaw Model Ladder Fix ===\n")
    print(f"Config: {config_path}")

    # Load current config
    try:
        cfg = json.loads(config_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"ERROR: Config is not valid JSON: {e}", file=sys.stderr)
        return 1

    # Compute before hash
    hash_before = sha256_file(config_path)
    print(f"SHA256 (before): {hash_before[:16]}...")

    # Apply fixes
    fixed_cfg, changes = apply_ladder_fixes(cfg)

    if not changes:
        print("\nNo changes needed - ladder configuration is valid.")
        return 0

    print("\nProposed changes:")
    for i, change in enumerate(changes, 1):
        print(f"  {i}. {change}")

    if args.dry_run:
        print("\nDRY RUN - no changes applied.")
        return 0

    # Create backup
    timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    backup_dir = config_path.parent / "backups"
    backup_dir.mkdir(exist_ok=True)
    backup_path = backup_dir / f"openclaw.json.{timestamp}.backup"

    shutil.copy2(config_path, backup_path)
    print(f"\nBackup created: {backup_path}")

    # Write fixed config atomically
    temp_path = config_path.with_suffix(".tmp")
    temp_path.write_text(json.dumps(fixed_cfg, indent=2, sort_keys=False), encoding="utf-8")
    temp_path.replace(config_path)

    # Compute after hash
    hash_after = sha256_file(config_path)
    print(f"SHA256 (after):  {hash_after[:16]}...")

    # Write audit capsule
    capsule_path = backup_dir / f"ladder_fix_{timestamp}.audit.json"
    audit = {
        "timestamp": timestamp,
        "config_path": str(config_path),
        "backup_path": str(backup_path),
        "sha256_before": hash_before,
        "sha256_after": hash_after,
        "changes": changes,
        "execution_ladder": EXECUTION_BASE,
        "thinking_ladder": THINKING_BASE,
    }
    capsule_path.write_text(json.dumps(audit, indent=2), encoding="utf-8")
    print(f"Audit capsule: {capsule_path}")

    print("\nFix applied successfully.")
    print("NEXT: Run 'coo models status' to verify ladder health")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

````

### File: `runtime/tools/workflow_pack.py`

````text
"""Workflow pack helpers for low-friction multi-agent handoffs."""

from __future__ import annotations

import json
import os
import re
import shlex
import subprocess
import sys
from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path
from typing import Iterable, Sequence

from runtime.util.atomic_write import atomic_write_text

# Import for BACKLOG parsing (will handle import error gracefully)
try:
    from recursive_kernel.backlog_parser import ItemStatus, mark_item_done, parse_backlog
except ImportError:
    parse_backlog = None
    mark_item_done = None
    ItemStatus = None


ACTIVE_WORK_RELATIVE_PATH = Path(".context/active_work.yaml")


def _unique_ordered(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        item = value.strip()
        if not item or item in seen:
            continue
        seen.add(item)
        out.append(item)
    return out


def build_active_work_payload(
    *,
    branch: str,
    latest_commits: Sequence[str],
    focus: Sequence[str],
    tests_targeted: Sequence[str],
    findings_open: Sequence[dict[str, str]],
) -> dict:
    """Build normalized active-work payload."""
    normalized_findings = []
    for finding in findings_open:
        finding_id = str(finding.get("id", "")).strip()
        severity = str(finding.get("severity", "")).strip().lower()
        status = str(finding.get("status", "")).strip().lower()
        if not finding_id or not severity or not status:
            continue
        normalized_findings.append(
            {"id": finding_id, "severity": severity, "status": status}
        )

    return {
        "version": "1.0",
        "branch": branch.strip() or "unknown",
        "latest_commits": _unique_ordered(latest_commits),
        "focus": _unique_ordered(focus),
        "tests_targeted": _unique_ordered(tests_targeted),
        "findings_open": normalized_findings,
    }


def write_active_work(repo_root: Path, payload: dict) -> Path:
    """Write .context/active_work.yaml deterministically."""
    output_path = Path(repo_root) / ACTIVE_WORK_RELATIVE_PATH
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(payload, indent=2) + "\n",
        encoding="utf-8",
    )
    return output_path


def read_active_work(repo_root: Path) -> dict:
    """Read .context/active_work.yaml, returning a normalized fallback when absent."""
    input_path = Path(repo_root) / ACTIVE_WORK_RELATIVE_PATH
    if not input_path.exists():
        return build_active_work_payload(
            branch="unknown",
            latest_commits=[],
            focus=[],
            tests_targeted=[],
            findings_open=[],
        )
    try:
        loaded = json.loads(input_path.read_text(encoding="utf-8")) or {}
    except json.JSONDecodeError:
        loaded = {}
    if not isinstance(loaded, dict):
        loaded = {}
    return build_active_work_payload(
        branch=str(loaded.get("branch", "unknown")),
        latest_commits=loaded.get("latest_commits") or [],
        focus=loaded.get("focus") or [],
        tests_targeted=loaded.get("tests_targeted") or [],
        findings_open=loaded.get("findings_open") or [],
    )


def _matches(file_path: str, prefixes: Sequence[str]) -> bool:
    return any(file_path == prefix or file_path.startswith(prefix) for prefix in prefixes)


def route_targeted_tests(changed_files: Sequence[str]) -> list[str]:
    """Map changed files to targeted test commands."""
    files = _unique_ordered(changed_files)

    routed: list[str] = []

    def add(command: str) -> None:
        if command not in routed:
            routed.append(command)

    for file_path in files:
        if _matches(
            file_path,
            (
                "runtime/orchestration/openclaw_bridge.py",
                "runtime/tests/orchestration/test_openclaw_bridge.py",
            ),
        ):
            add("pytest -q runtime/tests/orchestration/test_openclaw_bridge.py")
            continue

        if _matches(
            file_path,
            (
                "runtime/orchestration/missions/autonomous_build_cycle.py",
                "runtime/tests/orchestration/missions/test_autonomous_loop.py",
            ),
        ):
            add("pytest -q runtime/tests/orchestration/missions/test_autonomous_loop.py")
            continue

        if _matches(
            file_path,
            (
                "runtime/agents/api.py",
                "runtime/agents/opencode_client.py",
                "runtime/tests/test_agent_api_usage_plumbing.py",
                "tests/test_agent_api.py",
            ),
        ):
            add(
                "pytest -q runtime/tests/test_agent_api_usage_plumbing.py tests/test_agent_api.py"
            )
            continue

        if _matches(
            file_path,
            (
                "runtime/tools/workflow_pack.py",
                "runtime/tests/test_workflow_pack.py",
                "scripts/workflow/",
            ),
        ):
            add("pytest -q runtime/tests/test_workflow_pack.py")
            continue

        if _matches(
            file_path,
            (
                "runtime/tools/openclaw_models_preflight.sh",
                "runtime/tools/openclaw_model_policy_assert.py",
                "runtime/tools/openclaw_policy_assert.py",
                "runtime/tests/test_openclaw_model_policy_assert.py",
                "runtime/tests/test_openclaw_policy_assert.py",
                "runtime/tests/test_openclaw_memory_policy_assert.py",
            ),
        ):
            add(
                "pytest -q runtime/tests/test_openclaw_model_policy_assert.py "
                "runtime/tests/test_openclaw_policy_assert.py "
                "runtime/tests/test_openclaw_memory_policy_assert.py"
            )
            continue

    if not routed:
        routed.append("pytest -q runtime/tests")
    return routed


def discover_changed_files(repo_root: Path) -> list[str]:
    """Discover changed files with staged-first precedence."""
    repo = Path(repo_root)
    probes = [
        ["git", "-C", str(repo), "diff", "--name-only", "--cached"],
        ["git", "-C", str(repo), "diff", "--name-only"],
        ["git", "-C", str(repo), "diff", "--name-only", "HEAD~1..HEAD"],
    ]
    for cmd in probes:
        proc = subprocess.run(cmd, check=False, capture_output=True, text=True)
        if proc.returncode != 0:
            continue
        files = [line.strip() for line in proc.stdout.splitlines() if line.strip()]
        if files:
            return _unique_ordered(files)
    return []


def run_closure_tests(repo_root: Path, changed_files: Sequence[str]) -> dict:
    """Run targeted closure tests derived from changed files."""
    commands = route_targeted_tests(changed_files)
    commands_run: list[str] = []
    failures: list[str] = []
    passed_count = 0

    for command in commands:
        commands_run.append(command)
        proc = subprocess.run(
            shlex.split(command),
            check=False,
            cwd=Path(repo_root),
            capture_output=True,
            text=True,
        )
        if proc.returncode == 0:
            passed_count += 1
            continue
        stderr = (proc.stderr or "").strip()
        stdout = (proc.stdout or "").strip()
        details = stderr or stdout or f"exit code {proc.returncode}"
        failures.append(f"{command}: {details}")

    passed = not failures
    summary = f"{passed_count}/{len(commands_run)} targeted test command(s) passed."
    if failures:
        summary += f" Failures: {len(failures)}."

    return {
        "passed": passed,
        "commands_run": commands_run,
        "summary": summary,
        "failures": failures,
    }


def check_doc_stewardship(
    repo_root: Path,
    changed_files: Sequence[str],
    auto_fix: bool = True,
) -> dict:
    """Run doc stewardship gate only when docs paths are present."""
    docs_changed = any(path == "docs" or path.startswith("docs/") for path in changed_files)
    if not docs_changed:
        return {
            "required": False,
            "passed": True,
            "errors": [],
            "auto_fixed": False,
        }

    errors = []

    # Check if docs/11_admin/ files changed -> run admin validators
    admin_changed = any(
        path == "docs/11_admin" or path.startswith("docs/11_admin/")
        for path in changed_files
    )

    if admin_changed:
        # Admin structure check (always blocking)
        admin_struct_proc = subprocess.run(
            [sys.executable, "-m", "doc_steward.cli", "admin-structure-check", str(repo_root)],
            check=False,
            cwd=Path(repo_root),
            capture_output=True,
            text=True,
        )
        if admin_struct_proc.returncode != 0:
            errors.append(f"Admin structure check failed:\n{admin_struct_proc.stdout}")

        # Admin archive link ban check (always blocking)
        admin_archive_proc = subprocess.run(
            [sys.executable, "-m", "doc_steward.cli", "admin-archive-link-ban-check", str(repo_root)],
            check=False,
            cwd=Path(repo_root),
            capture_output=True,
            text=True,
        )
        if admin_archive_proc.returncode != 0:
            errors.append(f"Admin archive link ban check failed:\n{admin_archive_proc.stdout}")

        # Freshness check (mode-gated: off/warn/block)
        freshness_proc = subprocess.run(
            [sys.executable, "-m", "doc_steward.cli", "freshness-check", str(repo_root)],
            check=False,
            cwd=Path(repo_root),
            capture_output=True,
            text=True,
        )
        if freshness_proc.returncode != 0:
            errors.append(f"Freshness check failed:\n{freshness_proc.stdout}")

    # Check if docs/02_protocols/ files changed -> run protocols validators
    protocols_changed = any(
        path == "docs/02_protocols" or path.startswith("docs/02_protocols/")
        for path in changed_files
    )

    if protocols_changed:
        # Protocols structure check (always blocking)
        protocols_struct_proc = subprocess.run(
            [sys.executable, "-m", "doc_steward.cli", "protocols-structure-check", str(repo_root)],
            check=False,
            cwd=Path(repo_root),
            capture_output=True,
            text=True,
        )
        if protocols_struct_proc.returncode != 0:
            errors.append(f"Protocols structure check failed:\n{protocols_struct_proc.stdout}")

        # Artefact index check (always blocking)
        protocols_index_proc = subprocess.run(
            [sys.executable, "-m", "doc_steward.cli", "artefact-index-check", str(repo_root), "--directory", "docs/02_protocols"],
            check=False,
            cwd=Path(repo_root),
            capture_output=True,
            text=True,
        )
        if protocols_index_proc.returncode != 0:
            errors.append(f"Protocols artefact index check failed:\n{protocols_index_proc.stdout}")

        # Global archive link ban check (always blocking)
        protocols_link_proc = subprocess.run(
            [sys.executable, "-m", "doc_steward.cli", "docs-archive-link-ban-check", str(repo_root)],
            check=False,
            cwd=Path(repo_root),
            capture_output=True,
            text=True,
        )
        if protocols_link_proc.returncode != 0:
            errors.append(f"Archive link ban check failed:\n{protocols_link_proc.stdout}")

    # Check if docs/03_runtime/ files changed -> run runtime validators
    runtime_changed = any(
        path == "docs/03_runtime" or path.startswith("docs/03_runtime/")
        for path in changed_files
    )

    if runtime_changed:
        # Runtime structure check (always blocking)
        runtime_struct_proc = subprocess.run(
            [sys.executable, "-m", "doc_steward.cli", "runtime-structure-check", str(repo_root)],
            check=False,
            cwd=Path(repo_root),
            capture_output=True,
            text=True,
        )
        if runtime_struct_proc.returncode != 0:
            errors.append(f"Runtime structure check failed:\n{runtime_struct_proc.stdout}")

        # Artefact index check (always blocking)
        runtime_index_proc = subprocess.run(
            [sys.executable, "-m", "doc_steward.cli", "artefact-index-check", str(repo_root), "--directory", "docs/03_runtime"],
            check=False,
            cwd=Path(repo_root),
            capture_output=True,
            text=True,
        )
        if runtime_index_proc.returncode != 0:
            errors.append(f"Runtime artefact index check failed:\n{runtime_index_proc.stdout}")

        # Global archive link ban check (always blocking)
        runtime_link_proc = subprocess.run(
            [sys.executable, "-m", "doc_steward.cli", "docs-archive-link-ban-check", str(repo_root)],
            check=False,
            cwd=Path(repo_root),
            capture_output=True,
            text=True,
        )
        if runtime_link_proc.returncode != 0:
            errors.append(f"Archive link ban check failed:\n{runtime_link_proc.stdout}")

    # Check if docs/99_archive/ files changed -> run archive validators
    archive_changed = any(
        path == "docs/99_archive" or path.startswith("docs/99_archive/")
        for path in changed_files
    )

    if archive_changed:
        # Archive structure check (always blocking)
        archive_struct_proc = subprocess.run(
            [sys.executable, "-m", "doc_steward.cli", "archive-structure-check", str(repo_root)],
            check=False,
            cwd=Path(repo_root),
            capture_output=True,
            text=True,
        )
        if archive_struct_proc.returncode != 0:
            errors.append(f"Archive structure check failed:\n{archive_struct_proc.stdout}")

    # Run existing canonical doc stewardship gate (unchanged)
    cmd = [sys.executable, "scripts/claude_doc_stewardship_gate.py"]
    if auto_fix:
        cmd.append("--auto-fix")

    proc = subprocess.run(
        cmd,
        check=False,
        cwd=Path(repo_root),
        capture_output=True,
        text=True,
    )

    payload: dict = {}
    stdout = (proc.stdout or "").strip()
    if stdout:
        try:
            loaded = json.loads(stdout)
        except json.JSONDecodeError:
            loaded = {}
        if isinstance(loaded, dict):
            payload = loaded

    for item in payload.get("errors", []):
        text = str(item).strip()
        if text:
            errors.append(text)
    if not payload and proc.returncode != 0:
        stderr = (proc.stderr or "").strip()
        errors.append(stderr or "doc stewardship gate returned non-zero without JSON output")

    passed = (not errors) and bool(payload.get("passed")) and proc.returncode == 0
    auto_fixed = bool(payload.get("auto_fix_applied") or payload.get("auto_fix_success"))

    return {
        "required": True,
        "passed": passed,
        "errors": errors,
        "auto_fixed": auto_fixed,
        "docs_files": payload.get("docs_files", []),
    }


def merge_to_main(repo_root: Path, branch: str) -> dict:
    """Merge a feature branch into main using squash merge."""
    source_branch = branch.strip()
    if not source_branch:
        return {"success": False, "merge_sha": None, "errors": ["source branch is empty"]}
    if source_branch in {"main", "master"}:
        return {
            "success": False,
            "merge_sha": None,
            "errors": [f"cannot merge protected branch '{source_branch}'"],
        }

    repo = Path(repo_root)
    errors: list[str] = []

    safety = subprocess.run(
        [sys.executable, "scripts/repo_safety_gate.py", "--operation", "merge"],
        check=False,
        cwd=repo,
        capture_output=True,
        text=True,
    )
    if safety.returncode != 0:
        details = (safety.stderr or "").strip() or (safety.stdout or "").strip()
        return {
            "success": False,
            "merge_sha": None,
            "errors": [f"safety gate blocked merge: {details or 'unknown failure'}"],
        }

    steps = [
        ("checkout main", ["git", "-C", str(repo), "checkout", "main"]),
        ("pull --ff-only", ["git", "-C", str(repo), "pull", "--ff-only"]),
        ("squash merge", ["git", "-C", str(repo), "merge", "--squash", source_branch]),
        (
            "commit squash merge",
            ["git", "-C", str(repo), "commit", "-m", f"feat: Merge {source_branch} (squashed)"],
        ),
    ]

    for label, cmd in steps:
        run_env = None
        if label == "commit squash merge":
            run_env = os.environ.copy()
            run_env["LIFEOS_MAIN_COMMIT_ALLOWED"] = "1"
        proc = subprocess.run(
            cmd,
            check=False,
            capture_output=True,
            text=True,
            env=run_env,
        )
        if proc.returncode == 0:
            continue
        details = (proc.stderr or "").strip() or (proc.stdout or "").strip()
        if label == "pull --ff-only":
            lowered = details.lower()
            offline_markers = (
                "could not resolve hostname",
                "temporary failure in name resolution",
                "could not read from remote repository",
                "failed to connect",
            )
            if any(marker in lowered for marker in offline_markers):
                # Offline fallback: proceed with local main if remote is unreachable.
                continue
        errors.append(f"{label} failed: {details or f'exit code {proc.returncode}'}")
        subprocess.run(
            ["git", "-C", str(repo), "checkout", source_branch],
            check=False,
            capture_output=True,
            text=True,
        )
        return {"success": False, "merge_sha": None, "errors": errors}

    head = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "HEAD"],
        check=False,
        capture_output=True,
        text=True,
    )
    merge_sha = head.stdout.strip() if head.returncode == 0 else None
    if not merge_sha:
        errors.append("failed to resolve merge commit SHA")
        return {"success": False, "merge_sha": None, "errors": errors}

    return {"success": True, "merge_sha": merge_sha, "errors": []}


def cleanup_after_merge(repo_root: Path, branch: str, clear_context: bool = True) -> dict:
    """Cleanup local branch and active context artifact after merge."""
    repo = Path(repo_root)
    source_branch = branch.strip()

    errors: list[str] = []
    branch_deleted = False
    if source_branch and source_branch not in {"main", "master"}:
        proc = subprocess.run(
            ["git", "-C", str(repo), "branch", "-d", source_branch],
            check=False,
            capture_output=True,
            text=True,
        )
        if proc.returncode == 0:
            branch_deleted = True
        else:
            details = (proc.stderr or "").strip() or (proc.stdout or "").strip()
            errors.append(
                f"failed to delete local branch '{source_branch}': {details or f'exit code {proc.returncode}'}"
            )

    context_path = repo / ACTIVE_WORK_RELATIVE_PATH
    context_cleared = False
    if clear_context:
        try:
            if context_path.exists():
                context_path.unlink()
            context_cleared = not context_path.exists()
        except OSError as exc:
            errors.append(f"failed to clear {ACTIVE_WORK_RELATIVE_PATH}: {exc}")

    return {
        "branch_deleted": branch_deleted,
        "context_cleared": context_cleared,
        "errors": errors,
    }


def _extract_win_details(
    repo_root: Path,
    branch: str,
    merge_sha: str,
    test_summary: str,
) -> dict:
    """
    Extract meaningful Recent Win entry from branch and commits.

    Args:
        repo_root: Repository root path
        branch: Branch name (e.g., "build/doc-refresh-and-test-debt")
        merge_sha: Merge commit SHA
        test_summary: Test summary string from test run

    Returns:
        dict with keys: title, details, merge_sha_short
    """
    # Extract title from branch name
    # Remove prefixes like "build/", "fix/", "hotfix/", "spike/"
    title_raw = re.sub(r"^(build|fix|hotfix|spike)/", "", branch)
    # Replace hyphens/underscores with spaces and title-case
    title_words = re.split(r"[-_]+", title_raw)
    title = " ".join(word.capitalize() for word in title_words if word)

    # Get commit messages
    commits_output = ""
    proc = subprocess.run(
        ["git", "-C", str(repo_root), "log", "--format=%s", f"{branch}", "--not", "main"],
        check=False,
        capture_output=True,
        text=True,
    )
    if proc.returncode == 0:
        commits_output = proc.stdout.strip()

    # Build details from commits
    if commits_output:
        commit_lines = [line.strip() for line in commits_output.splitlines() if line.strip()]
        # Truncate to first 5 if too many
        if len(commit_lines) > 5:
            details = "; ".join(commit_lines[:5]) + f" (and {len(commit_lines) - 5} more)"
        else:
            details = "; ".join(commit_lines)
    else:
        # Fallback to title if git log fails
        details = title

    # Include test metrics if non-trivial
    if test_summary and "passed" in test_summary.lower():
        details += f" — {test_summary}"

    return {
        "title": title,
        "details": details,
        "merge_sha_short": merge_sha[:7],
    }


def _update_lifeos_state(
    state_path: Path,
    title: str,
    details: str,
    merge_sha_short: str,
    skip_on_error: bool = True,
) -> dict:
    """
    Update LIFEOS_STATE.md with Recent Win and timestamp.

    Args:
        state_path: Path to LIFEOS_STATE.md
        title: Win title (e.g., "Doc Refresh And Test Debt")
        details: Win details (e.g., "Fixed bugs; Added tests")
        merge_sha_short: Short merge SHA (7 chars)
        skip_on_error: If True, return error dict instead of raising

    Returns:
        dict with keys: success (bool), errors (list)
    """
    errors = []

    if not state_path.exists():
        msg = f"STATE file not found: {state_path}"
        if skip_on_error:
            return {"success": False, "errors": [msg]}
        raise FileNotFoundError(msg)

    try:
        content = state_path.read_text(encoding="utf-8")
    except Exception as exc:
        msg = f"Failed to read STATE file: {exc}"
        if skip_on_error:
            return {"success": False, "errors": [msg]}
        raise

    # Update Last Updated timestamp and revision
    today = datetime.now().strftime("%Y-%m-%d")

    def increment_revision(match):
        rev_str = match.group(1)
        try:
            rev_num = int(rev_str)
            return f"**Last Updated:** {today} (rev{rev_num + 1})"
        except ValueError:
            # If can't parse, just use (updated)
            return f"**Last Updated:** {today} (updated)"

    # Try to update Last Updated line with revision increment
    updated_content, num_subs = re.subn(
        r"\*\*Last Updated:\*\* \d{4}-\d{2}-\d{2} \(rev(\d+)\)",
        increment_revision,
        content,
    )

    # If no match with revision, try without revision
    if num_subs == 0:
        updated_content = re.sub(
            r"\*\*Last Updated:\*\* \d{4}-\d{2}-\d{2}",
            f"**Last Updated:** {today}",
            content,
        )

    # Find the Recent Wins section and add new entry
    recent_wins_pattern = r"(## 🟩 Recent Wins\s*\n)"
    new_win_entry = f"- **{today}:** {title} — {details} (merge commit {merge_sha_short})\n"

    match = re.search(recent_wins_pattern, updated_content)
    if match:
        # Insert new win right after the section header
        insert_pos = match.end()
        updated_content = (
            updated_content[:insert_pos]
            + new_win_entry
            + updated_content[insert_pos:]
        )
    else:
        # Recent Wins section not found - skip win addition
        msg = "Recent Wins section not found in STATE file"
        errors.append(msg)

    # Write atomically
    try:
        atomic_write_text(state_path, updated_content)
    except Exception as exc:
        msg = f"Failed to write STATE file: {exc}"
        if skip_on_error:
            return {"success": False, "errors": [msg]}
        raise

    return {"success": True, "errors": errors}


def _match_backlog_item(
    branch: str,
    commit_messages: list[str],
    backlog_items: list,
    threshold: float = 0.7,
):
    """
    Match branch/commits to BACKLOG items using fuzzy similarity.

    Args:
        branch: Branch name (e.g., "build/doc-refresh-and-test-debt")
        commit_messages: List of commit message subjects
        backlog_items: List of BacklogItem objects
        threshold: Minimum similarity score (0.0-1.0)

    Returns:
        Best matching BacklogItem or None if no match above threshold
    """
    if not backlog_items:
        return None

    # Extract keywords from branch and commits
    keywords = []
    # Remove branch prefix and split on hyphens/underscores
    branch_clean = re.sub(r"^(build|fix|hotfix|spike)/", "", branch)
    keywords.extend(re.split(r"[-_/]+", branch_clean.lower()))

    # Add words from commit messages
    for msg in commit_messages:
        keywords.extend(msg.lower().split())

    # Combine into a search string
    search_text = " ".join(keywords)

    # Score each BACKLOG item
    best_match = None
    best_score = 0.0

    for item in backlog_items:
        item_text = item.title.lower()
        # Use SequenceMatcher for fuzzy matching
        score = SequenceMatcher(None, search_text, item_text).ratio()

        # Also check for substring matches (boost score)
        for keyword in keywords:
            if len(keyword) > 3 and keyword in item_text:
                score += 0.15  # Boost for keyword match

        if score > best_score:
            best_score = score
            best_match = item

    if best_score >= threshold:
        return best_match

    return None


def _update_backlog_state(
    backlog_path: Path,
    branch: str,
    commit_messages: list[str],
    skip_on_error: bool = True,
) -> dict:
    """
    Update BACKLOG.md timestamp and mark matching items as done.

    Args:
        backlog_path: Path to BACKLOG.md
        branch: Branch name
        commit_messages: List of commit message subjects
        skip_on_error: If True, return error dict instead of raising

    Returns:
        dict with keys: success (bool), items_marked (int), errors (list)
    """
    errors = []
    items_marked = 0

    if not backlog_path.exists():
        msg = f"BACKLOG file not found: {backlog_path}"
        if skip_on_error:
            return {"success": False, "items_marked": 0, "errors": [msg]}
        raise FileNotFoundError(msg)

    # Update timestamp
    today = datetime.now().strftime("%Y-%m-%d")
    try:
        content = backlog_path.read_text(encoding="utf-8")
        updated_content = re.sub(
            r"\*\*Last Updated:\*\* \d{4}-\d{2}-\d{2}",
            f"**Last Updated:** {today}",
            content,
        )
        atomic_write_text(backlog_path, updated_content)
    except Exception as exc:
        msg = f"Failed to update BACKLOG timestamp: {exc}"
        if skip_on_error:
            return {"success": False, "items_marked": 0, "errors": [msg]}
        raise

    # Try to find and mark matching item
    if parse_backlog is None or mark_item_done is None:
        errors.append("backlog_parser not available (import failed)")
        return {"success": True, "items_marked": 0, "errors": errors}

    try:
        items = parse_backlog(backlog_path)
        # Filter to TODO items only
        todo_items = [item for item in items if item.status == ItemStatus.TODO]

        if todo_items:
            matched_item = _match_backlog_item(
                branch=branch,
                commit_messages=commit_messages,
                backlog_items=todo_items,
                threshold=0.3,  # Lower threshold to catch more matches
            )

            if matched_item:
                mark_item_done(backlog_path, matched_item)
                items_marked = 1
        else:
            errors.append("No TODO items found in BACKLOG")

    except Exception as exc:
        msg = f"Failed to mark BACKLOG item: {exc}"
        if skip_on_error:
            errors.append(msg)
        else:
            raise

    return {"success": True, "items_marked": items_marked, "errors": errors}


def update_state_and_backlog(
    repo_root: Path,
    branch: str,
    merge_sha: str,
    test_summary: str,
    skip_on_error: bool = True,
) -> dict:
    """
    Orchestrate STATE and BACKLOG updates after successful merge.

    Args:
        repo_root: Repository root path
        branch: Branch name (e.g., "build/test-debt-stabilization")
        merge_sha: Merge commit SHA
        test_summary: Test summary string from test run
        skip_on_error: If True, continue on errors (warn, don't block)

    Returns:
        dict with keys:
            - state_updated (bool): STATE file was updated
            - backlog_updated (bool): BACKLOG file was updated
            - items_marked (int): Number of BACKLOG items marked done
            - errors (list): Any errors/warnings encountered
    """
    repo_root = Path(repo_root)
    errors = []
    state_updated = False
    backlog_updated = False
    items_marked = 0

    # Extract win details
    win_details = _extract_win_details(
        repo_root=repo_root,
        branch=branch,
        merge_sha=merge_sha,
        test_summary=test_summary,
    )

    # Get commit messages for BACKLOG matching
    commit_messages = []
    proc = subprocess.run(
        ["git", "-C", str(repo_root), "log", "--format=%s", f"{branch}", "--not", "main"],
        check=False,
        capture_output=True,
        text=True,
    )
    if proc.returncode == 0:
        commit_messages = [
            line.strip() for line in proc.stdout.splitlines() if line.strip()
        ]

    # Update STATE
    state_path = repo_root / "docs" / "11_admin" / "LIFEOS_STATE.md"
    state_result = _update_lifeos_state(
        state_path=state_path,
        title=win_details["title"],
        details=win_details["details"],
        merge_sha_short=win_details["merge_sha_short"],
        skip_on_error=skip_on_error,
    )
    state_updated = state_result["success"]
    errors.extend(state_result["errors"])

    # Update BACKLOG
    backlog_path = repo_root / "docs" / "11_admin" / "BACKLOG.md"
    backlog_result = _update_backlog_state(
        backlog_path=backlog_path,
        branch=branch,
        commit_messages=commit_messages,
        skip_on_error=skip_on_error,
    )
    backlog_updated = backlog_result["success"]
    items_marked = backlog_result.get("items_marked", 0)
    errors.extend(backlog_result["errors"])

    return {
        "state_updated": state_updated,
        "backlog_updated": backlog_updated,
        "items_marked": items_marked,
        "errors": errors,
    }

````

### File: `runtime/tests/test_openclaw_policy_assert.py`

````text
from runtime.tools.openclaw_policy_assert import assert_policy, command_authorized
from pathlib import Path

def _cfg():
    return {
        'commands': {'ownerAllowFrom': ['owner-1']},
        'agents': {
            'defaults': {
                'workspace': '/home/tester/.openclaw/workspace',
                'thinkingDefault': 'low',
                'model': {
                    'primary': 'openai-codex/gpt-5.3-codex',
                    'fallbacks': ['github-copilot/gpt-5-mini', 'google-gemini-cli/gemini-3-flash-preview'],
                },
                'memorySearch': {
                    'enabled': False,
                    'provider': 'local',
                    'fallback': 'none',
                    'sources': ['memory'],
                },
            },
            'list': [
                {'id': 'main', 'model': {'primary': 'openai-codex/gpt-5.3-codex', 'fallbacks': ['github-copilot/gpt-5-mini', 'google-gemini-cli/gemini-3-flash-preview']}},
                {'id': 'quick', 'model': {'primary': 'openai-codex/gpt-5.3-codex', 'fallbacks': ['github-copilot/gpt-5-mini', 'google-gemini-cli/gemini-3-flash-preview']}},
                {'id': 'think', 'model': {'primary': 'openai-codex/gpt-5.3-codex', 'fallbacks': ['github-copilot/gpt-5-mini', 'google-gemini-cli/gemini-3-flash-preview']}},
            ],
        },
    }

def test_assert_policy_passes_for_expected_ladders():
    cfg = _cfg()
    cfg['agents']['defaults']['workspace'] = str(Path.home() / '.openclaw' / 'workspace')
    result = assert_policy(cfg)
    assert result['owners'] == ['owner-1']
    assert result['defaults_thinking'] == 'low'
    assert result['required_subscription_fallbacks'] == ['github-copilot/gpt-5-mini', 'google-gemini-cli/gemini-3-flash-preview']
    assert result['memory']['enabled'] is False
    assert result['memory']['provider'] == 'local'
    assert result['memory']['fallback'] == 'none'

def test_non_owner_cannot_model_or_think_switch():
    cfg = _cfg()
    assert command_authorized(cfg, 'owner-1', '/model openai-codex/gpt-5.3-codex')
    assert not command_authorized(cfg, 'outsider', '/model openai-codex/gpt-5.3-codex')
    assert not command_authorized(cfg, 'outsider', '/think high')

````

### File: `runtime/tests/test_openclaw_memory_policy_assert.py`

````text
from runtime.tools.openclaw_policy_assert import assert_policy
from pathlib import Path


def _base_cfg():
    return {
        "commands": {"ownerAllowFrom": ["owner-1"]},
        "agents": {
            "defaults": {
                "workspace": "/home/tester/.openclaw/workspace",
                "thinkingDefault": "low",
                "model": {
                    "primary": "openai-codex/gpt-5.3-codex",
                    "fallbacks": ["github-copilot/gpt-5-mini", "google-gemini-cli/gemini-3-flash-preview"],
                },
                "memorySearch": {
                    "enabled": False,
                    "provider": "local",
                    "fallback": "none",
                    "sources": ["memory"],
                },
            },
            "list": [
                {"id": "main", "model": {"primary": "openai-codex/gpt-5.3-codex", "fallbacks": ["github-copilot/gpt-5-mini", "google-gemini-cli/gemini-3-flash-preview"]}},
                {"id": "quick", "model": {"primary": "openai-codex/gpt-5.3-codex", "fallbacks": ["github-copilot/gpt-5-mini", "google-gemini-cli/gemini-3-flash-preview"]}},
                {"id": "think", "model": {"primary": "openai-codex/gpt-5.3-codex", "fallbacks": ["github-copilot/gpt-5-mini", "google-gemini-cli/gemini-3-flash-preview"]}},
            ],
        },
    }


def test_memory_policy_accepts_local_no_fallback_and_memory_source_only():
    cfg = _base_cfg()
    cfg["agents"]["defaults"]["workspace"] = str(Path.home() / ".openclaw" / "workspace")
    result = assert_policy(cfg)
    assert result["memory"]["enabled"] is False
    assert result["memory"]["provider"] == "local"
    assert result["memory"]["fallback"] == "none"
    assert result["memory"]["sources"] == ["memory"]


def test_memory_policy_rejects_non_local_provider():
    cfg = _base_cfg()
    cfg["agents"]["defaults"]["workspace"] = str(Path.home() / ".openclaw" / "workspace")
    cfg["agents"]["defaults"]["memorySearch"]["provider"] = "openai"
    try:
        assert_policy(cfg)
    except AssertionError as exc:
        assert "memorySearch.provider must be local" in str(exc)
    else:
        raise AssertionError("expected memory provider assertion")


def test_memory_policy_rejects_sessions_source():
    cfg = _base_cfg()
    cfg["agents"]["defaults"]["workspace"] = str(Path.home() / ".openclaw" / "workspace")
    cfg["agents"]["defaults"]["memorySearch"]["sources"] = ["memory", "sessions"]
    try:
        assert_policy(cfg)
    except AssertionError as exc:
        assert 'must not include "sessions"' in str(exc)
    else:
        raise AssertionError("expected sessions source assertion")


def test_memory_policy_rejects_enabled_true_during_burn_in():
    cfg = _base_cfg()
    cfg["agents"]["defaults"]["workspace"] = str(Path.home() / ".openclaw" / "workspace")
    cfg["agents"]["defaults"]["memorySearch"]["enabled"] = True
    try:
        assert_policy(cfg)
    except AssertionError as exc:
        assert "memorySearch.enabled must be false during burn-in" in str(exc)
    else:
        raise AssertionError("expected memory enabled assertion")


def test_memory_policy_rejects_workspace_outside_openclaw_home():
    cfg = _base_cfg()
    cfg["agents"]["defaults"]["workspace"] = "/mnt/c/Users/cabra/Projects/LifeOS"
    try:
        assert_policy(cfg)
    except AssertionError as exc:
        assert "workspace must be under ~/.openclaw" in str(exc)
    else:
        raise AssertionError("expected workspace boundary assertion")

````

### File: `runtime/tests/test_openclaw_model_policy_assert.py`

````text
from runtime.tools.openclaw_model_policy_assert import (
    _discover_kimi_id,
    _parse_models_list_text,
    assert_policy,
)


def _cfg() -> dict:
    return {
        "agents": {
            "list": [
                {
                    "id": "main",
                    "model": {
                        "primary": "openai-codex/gpt-5.3-codex",
                        "fallbacks": [
                            "github-copilot/gpt-5-mini",
                            "google-gemini-cli/gemini-3-flash-preview",
                            "openrouter/openai/gpt-4.1-mini",
                        ],
                    },
                },
                {
                    "id": "quick",
                    "model": {
                        "primary": "openai-codex/gpt-5.3-codex",
                        "fallbacks": [
                            "github-copilot/gpt-5-mini",
                            "google-gemini-cli/gemini-3-flash-preview",
                        ],
                    },
                },
                {
                    "id": "think",
                    "thinking": "extra_high",
                    "model": {
                        "primary": "openai-codex/gpt-5.3-codex",
                        "fallbacks": [
                            "github-copilot/gpt-5-mini",
                            "google-gemini-cli/gemini-3-flash-preview",
                            "openrouter/openai/gpt-4.1-mini",
                        ],
                    },
                },
            ]
        }
    }


def _models_list_text() -> str:
    return """\
Model                                      Input      Ctx      Local Auth  Tags
openai-codex/gpt-5.3-codex                 text+image 266k     no    yes   configured
github-copilot/gpt-5-mini                  text+image 125k     no    yes   configured
google-gemini-cli/gemini-3-flash-preview   text+image 1024k    no    yes   configured
openrouter/openai/gpt-4.1-mini             text+image 200k     no    yes   configured
opencode/kimi-k2.5-free                    text+image 256k     no    yes   configured
"""


def test_policy_assert_passes_for_subscription_prefix_and_api_standby_tail():
    cfg = _cfg()
    status = _parse_models_list_text(_models_list_text())
    result = assert_policy(cfg, status, None)
    assert result["policy_ok"] is True
    assert result["ladders"]["main"]["working_count"] >= 1
    assert result["ladders"]["quick"]["working_count"] >= 1
    assert result["ladders"]["think"]["working_count"] >= 1


def test_policy_assert_fails_on_wrong_prefix_order():
    cfg = _cfg()
    cfg["agents"]["list"][0]["model"]["fallbacks"] = [
        "google-gemini-cli/gemini-3-flash-preview",
        "github-copilot/gpt-5-mini",
    ]
    status = _parse_models_list_text(_models_list_text())
    result = assert_policy(cfg, status, None)
    assert result["policy_ok"] is False
    assert any("prefix mismatch" in v for v in result["violations"])


def test_policy_assert_fails_on_disallowed_haiku():
    cfg = _cfg()
    cfg["agents"]["list"][1]["model"]["fallbacks"] = [
        "github-copilot/gpt-5-mini",
        "google-gemini-cli/gemini-3-flash-preview",
        "anthropic/claude-3-haiku-20240307",
    ]
    status = _parse_models_list_text(_models_list_text())
    result = assert_policy(cfg, status, None)
    assert result["policy_ok"] is False
    assert any("disallowed fallback" in v for v in result["violations"])


def test_policy_assert_fails_when_agent_has_no_working_models():
    cfg = _cfg()
    status = _parse_models_list_text(_models_list_text())
    for model_id in list(status.keys()):
        status[model_id]["working"] = False
    result = assert_policy(cfg, status, None)
    assert result["policy_ok"] is False
    assert any("no working model detected" in v for v in result["violations"])


def test_discover_kimi_id_retained_for_backward_compat():
    kimi = _discover_kimi_id([], ["opencode/kimi-k2.5-free"])
    assert kimi == "opencode/kimi-k2.5-free"

````

### File: `runtime/tests/test_workflow_pack.py`

````text
from __future__ import annotations

import json
import subprocess
from datetime import datetime
from pathlib import Path

from runtime.tools.workflow_pack import (
    build_active_work_payload,
    check_doc_stewardship,
    cleanup_after_merge,
    read_active_work,
    run_closure_tests,
    route_targeted_tests,
    write_active_work,
)


def test_active_work_roundtrip(tmp_path: Path) -> None:
    payload = build_active_work_payload(
        branch="feature/workflow-pack",
        latest_commits=["abc123 add router", "def456 add skills"],
        focus=["W4-T01", "W5-T04"],
        tests_targeted=["pytest -q runtime/tests/test_workflow_pack.py"],
        findings_open=[{"id": "M1", "severity": "moderate", "status": "open"}],
    )

    output = write_active_work(tmp_path, payload)
    assert output == tmp_path / ".context" / "active_work.yaml"

    loaded = read_active_work(tmp_path)
    assert loaded["version"] == "1.0"
    assert loaded["branch"] == "feature/workflow-pack"
    assert loaded["focus"] == ["W4-T01", "W5-T04"]
    assert loaded["findings_open"] == [{"id": "M1", "severity": "moderate", "status": "open"}]


def test_route_targeted_tests_routes_known_files() -> None:
    changed = [
        "runtime/orchestration/openclaw_bridge.py",
        "runtime/orchestration/missions/autonomous_build_cycle.py",
    ]
    commands = route_targeted_tests(changed)
    assert commands == [
        "pytest -q runtime/tests/orchestration/test_openclaw_bridge.py",
        "pytest -q runtime/tests/orchestration/missions/test_autonomous_loop.py",
    ]


def test_route_targeted_tests_deduplicates() -> None:
    changed = [
        "runtime/agents/api.py",
        "tests/test_agent_api.py",
        "runtime/agents/opencode_client.py",
    ]
    commands = route_targeted_tests(changed)
    assert commands == [
        "pytest -q runtime/tests/test_agent_api_usage_plumbing.py tests/test_agent_api.py",
    ]


def test_route_targeted_tests_routes_openclaw_model_preflight() -> None:
    commands = route_targeted_tests(["runtime/tools/openclaw_models_preflight.sh"])
    assert commands == [
        "pytest -q runtime/tests/test_openclaw_model_policy_assert.py "
        "runtime/tests/test_openclaw_policy_assert.py "
        "runtime/tests/test_openclaw_memory_policy_assert.py"
    ]


def test_route_targeted_tests_routes_openclaw_policy_bundle() -> None:
    commands = route_targeted_tests(["runtime/tools/openclaw_policy_assert.py"])
    assert commands == [
        "pytest -q runtime/tests/test_openclaw_model_policy_assert.py "
        "runtime/tests/test_openclaw_policy_assert.py "
        "runtime/tests/test_openclaw_memory_policy_assert.py"
    ]


def test_route_targeted_tests_fallback() -> None:
    commands = route_targeted_tests(["docs/11_admin/BACKLOG.md"])
    assert commands == ["pytest -q runtime/tests"]


def test_run_closure_tests_passes_on_zero_returncode(monkeypatch) -> None:
    def fake_run(*args, **kwargs):
        return subprocess.CompletedProcess(args=args[0], returncode=0, stdout="ok", stderr="")

    monkeypatch.setattr("runtime.tools.workflow_pack.subprocess.run", fake_run)
    result = run_closure_tests(Path("."), ["runtime/tools/workflow_pack.py"])
    assert result["passed"] is True
    assert result["commands_run"] == ["pytest -q runtime/tests/test_workflow_pack.py"]


def test_run_closure_tests_fails_on_nonzero(monkeypatch) -> None:
    def fake_run(*args, **kwargs):
        return subprocess.CompletedProcess(
            args=args[0],
            returncode=1,
            stdout="",
            stderr="failed",
        )

    monkeypatch.setattr("runtime.tools.workflow_pack.subprocess.run", fake_run)
    result = run_closure_tests(Path("."), ["runtime/tools/workflow_pack.py"])
    assert result["passed"] is False
    assert result["failures"]


def test_check_doc_stewardship_skips_when_no_docs(monkeypatch) -> None:
    def fail_if_called(*args, **kwargs):
        raise AssertionError("subprocess should not be called")

    monkeypatch.setattr("runtime.tools.workflow_pack.subprocess.run", fail_if_called)
    result = check_doc_stewardship(Path("."), ["runtime/tools/workflow_pack.py"])
    assert result["required"] is False
    assert result["passed"] is True


def test_check_doc_stewardship_runs_when_docs_changed(monkeypatch) -> None:
    payload = {
        "passed": True,
        "docs_modified": True,
        "docs_files": ["docs/INDEX.md"],
        "errors": [],
    }

    def fake_run(*args, **kwargs):
        return subprocess.CompletedProcess(
            args=args[0],
            returncode=0,
            stdout=json.dumps(payload),
            stderr="",
        )

    monkeypatch.setattr("runtime.tools.workflow_pack.subprocess.run", fake_run)
    result = check_doc_stewardship(Path("."), ["docs/INDEX.md"])
    assert result["required"] is True
    assert result["passed"] is True
    assert result["docs_files"] == ["docs/INDEX.md"]


def test_cleanup_after_merge_clears_context(tmp_path: Path, monkeypatch) -> None:
    context_path = tmp_path / ".context" / "active_work.yaml"
    context_path.parent.mkdir(parents=True, exist_ok=True)
    context_path.write_text("{}", encoding="utf-8")

    def fake_run(*args, **kwargs):
        return subprocess.CompletedProcess(args=args[0], returncode=0, stdout="", stderr="")

    monkeypatch.setattr("runtime.tools.workflow_pack.subprocess.run", fake_run)
    result = cleanup_after_merge(tmp_path, "build/feature", clear_context=True)
    assert result["branch_deleted"] is True
    assert result["context_cleared"] is True
    assert not context_path.exists()


# --- Tests for STATE/BACKLOG update functions ---


def test_extract_win_details_from_branch(monkeypatch) -> None:
    """Test extraction of win details from branch name and commits."""
    from runtime.tools.workflow_pack import _extract_win_details

    fake_commits = "feat: fix test debt\nchore: update docs\ntest: add coverage"

    def fake_run(*args, **kwargs):
        if "git" in args[0] and "log" in args[0]:
            return subprocess.CompletedProcess(
                args=args[0], returncode=0, stdout=fake_commits, stderr=""
            )
        return subprocess.CompletedProcess(args=args[0], returncode=0, stdout="", stderr="")

    monkeypatch.setattr("runtime.tools.workflow_pack.subprocess.run", fake_run)

    result = _extract_win_details(
        repo_root=Path("/fake/repo"),
        branch="build/doc-refresh-and-test-debt",
        merge_sha="abc123def456",
        test_summary="3/3 targeted test command(s) passed.",
    )

    assert result["title"] == "Doc Refresh And Test Debt"
    assert "fix test debt" in result["details"].lower()
    assert result["merge_sha_short"] == "abc123d"


def test_update_lifeos_state_adds_recent_win(tmp_path: Path) -> None:
    """Test that STATE update adds Recent Win and updates timestamp."""
    from runtime.tools.workflow_pack import _update_lifeos_state

    state_path = tmp_path / "docs" / "11_admin" / "LIFEOS_STATE.md"
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(
        """# LifeOS State

**Last Updated:** 2026-02-12 (rev3)

## 🟩 Recent Wins

- **2026-02-12:** Old win entry
- **2026-02-11:** Another old win
""",
        encoding="utf-8",
    )

    result = _update_lifeos_state(
        state_path=state_path,
        title="Doc Refresh And Test Debt",
        details="Fixed test debt; Updated docs; Added coverage",
        merge_sha_short="abc123d",
        skip_on_error=True,
    )

    assert result["success"] is True
    assert result["errors"] == []

    content = state_path.read_text(encoding="utf-8")
    today = datetime.now().strftime("%Y-%m-%d")
    # Should have new win at the top
    assert f"**{today}:** Doc Refresh And Test Debt — Fixed test debt" in content
    assert "(merge commit abc123d)" in content
    # Should have updated timestamp with rev4
    assert f"**Last Updated:** {today} (rev4)" in content


def test_update_lifeos_state_increments_revision(tmp_path: Path) -> None:
    """Test that revision number increments correctly."""
    from runtime.tools.workflow_pack import _update_lifeos_state

    state_path = tmp_path / "docs" / "11_admin" / "LIFEOS_STATE.md"
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(
        """# LifeOS State

**Last Updated:** 2026-01-15 (rev10)

## 🟩 Recent Wins

- **2026-01-15:** Some win
""",
        encoding="utf-8",
    )

    result = _update_lifeos_state(
        state_path=state_path,
        title="Test",
        details="Test details",
        merge_sha_short="xyz789a",
        skip_on_error=True,
    )

    assert result["success"] is True
    content = state_path.read_text(encoding="utf-8")
    today = datetime.now().strftime("%Y-%m-%d")
    # Should increment from rev10 to rev11
    assert f"**Last Updated:** {today} (rev11)" in content


def test_match_backlog_item_finds_match() -> None:
    """Test that BACKLOG item matching works with fuzzy similarity."""
    from runtime.tools.workflow_pack import _match_backlog_item
    from recursive_kernel.backlog_parser import BacklogItem, ItemStatus, Priority

    # Create mock backlog items
    items = [
        BacklogItem(
            item_key="abc123",
            item_key_full="abc123full",
            priority=Priority.P1,
            title="Fix test_steward_runner.py (25/27 failing)",
            dod="Tests pass",
            owner="antigravity",
            status=ItemStatus.TODO,
            context="Import/fixture issues",
            line_number=26,
            original_line="- [ ] **Fix test_steward_runner.py (25/27 failing)**",
        ),
        BacklogItem(
            item_key="def456",
            item_key_full="def456full",
            priority=Priority.P1,
            title="Fix test_e2e_smoke_timeout.py (import error)",
            dod="Import fixed",
            owner="antigravity",
            status=ItemStatus.TODO,
            context="",
            line_number=27,
            original_line="- [ ] **Fix test_e2e_smoke_timeout.py (import error)**",
        ),
    ]

    # Branch name with "test debt" should match first item
    result = _match_backlog_item(
        branch="build/doc-refresh-and-test-debt",
        commit_messages=["fix test_steward_runner", "update docs"],
        backlog_items=items,
        threshold=0.3,  # Lower threshold for testing
    )

    assert result is not None
    assert "test" in result.title.lower()


def test_match_backlog_item_no_match_below_threshold() -> None:
    """Test that no match is returned if similarity is below threshold."""
    from runtime.tools.workflow_pack import _match_backlog_item
    from recursive_kernel.backlog_parser import BacklogItem, ItemStatus, Priority

    items = [
        BacklogItem(
            item_key="abc123",
            item_key_full="abc123full",
            priority=Priority.P0,
            title="OpenClaw installation",
            dod="Installed",
            owner="antigravity",
            status=ItemStatus.TODO,
            context="",
            line_number=10,
            original_line="- [ ] **OpenClaw installation**",
        ),
    ]

    # Completely different branch should not match
    result = _match_backlog_item(
        branch="build/ui-theme-colors",
        commit_messages=["change button colors"],
        backlog_items=items,
        threshold=0.7,
    )

    assert result is None


def test_update_backlog_marks_item_done(tmp_path: Path) -> None:
    """Test that BACKLOG update marks matched items as done."""
    from runtime.tools.workflow_pack import _update_backlog_state

    backlog_path = tmp_path / "docs" / "11_admin" / "BACKLOG.md"
    backlog_path.parent.mkdir(parents=True, exist_ok=True)
    backlog_path.write_text(
        """# BACKLOG

**Last Updated:** 2026-02-12

## Now

### P1 (High)

- [ ] **Fix test_steward_runner.py (25/27 failing)** — DoD: Tests pass — Owner: antigravity
- [ ] **Fix test_e2e_smoke_timeout.py** — DoD: Import fixed — Owner: antigravity
""",
        encoding="utf-8",
    )

    result = _update_backlog_state(
        backlog_path=backlog_path,
        branch="build/test-debt-stabilization",
        commit_messages=["fix test_steward_runner", "add tests"],
        skip_on_error=True,
    )

    assert result["success"] is True
    content = backlog_path.read_text(encoding="utf-8")
    today = datetime.now().strftime("%Y-%m-%d")
    # Should update timestamp
    assert f"**Last Updated:** {today}" in content
    # Should mark matching item as done
    assert "[x] **Fix test_steward_runner.py" in content


def test_update_backlog_updates_timestamp_only_if_no_match(tmp_path: Path) -> None:
    """Test that BACKLOG timestamp updates even if no item matches."""
    from runtime.tools.workflow_pack import _update_backlog_state

    backlog_path = tmp_path / "docs" / "11_admin" / "BACKLOG.md"
    backlog_path.parent.mkdir(parents=True, exist_ok=True)
    backlog_path.write_text(
        """# BACKLOG

**Last Updated:** 2026-02-10

## Now

- [ ] **Some unrelated task** — DoD: Done — Owner: antigravity
""",
        encoding="utf-8",
    )

    result = _update_backlog_state(
        backlog_path=backlog_path,
        branch="build/ui-improvements",
        commit_messages=["change colors"],
        skip_on_error=True,
    )

    assert result["success"] is True
    content = backlog_path.read_text(encoding="utf-8")
    today = datetime.now().strftime("%Y-%m-%d")
    # Should update timestamp
    assert f"**Last Updated:** {today}" in content
    # Should NOT mark item as done
    assert "[ ] **Some unrelated task**" in content


def test_update_state_and_backlog_integration(tmp_path: Path, monkeypatch) -> None:
    """Test integration of STATE and BACKLOG updates."""
    from runtime.tools.workflow_pack import update_state_and_backlog

    # Create STATE file
    state_path = tmp_path / "docs" / "11_admin" / "LIFEOS_STATE.md"
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(
        """# LifeOS State

**Last Updated:** 2026-02-12 (rev3)

## 🟩 Recent Wins

- **2026-02-12:** Old win
""",
        encoding="utf-8",
    )

    # Create BACKLOG file
    backlog_path = tmp_path / "docs" / "11_admin" / "BACKLOG.md"
    backlog_path.write_text(
        """# BACKLOG

**Last Updated:** 2026-02-10

## Now

### P1 (High)

- [ ] **Fix test debt** — DoD: Tests pass — Owner: antigravity
""",
        encoding="utf-8",
    )

    # Mock git log
    def fake_run(*args, **kwargs):
        if "git" in args[0] and "log" in args[0]:
            return subprocess.CompletedProcess(
                args=args[0],
                returncode=0,
                stdout="fix: stabilize test suite",
                stderr="",
            )
        return subprocess.CompletedProcess(args=args[0], returncode=0, stdout="", stderr="")

    monkeypatch.setattr("runtime.tools.workflow_pack.subprocess.run", fake_run)

    result = update_state_and_backlog(
        repo_root=tmp_path,
        branch="build/test-debt-stabilization",
        merge_sha="abc123def456",
        test_summary="5/5 tests passed.",
        skip_on_error=True,
    )

    assert result["state_updated"] is True
    assert result["backlog_updated"] is True
    assert result["items_marked"] == 1
    assert result["errors"] == []

    # Verify STATE was updated
    state_content = state_path.read_text(encoding="utf-8")
    today = datetime.now().strftime("%Y-%m-%d")
    assert f"**{today}:** Test Debt Stabilization" in state_content
    assert "(merge commit abc123d)" in state_content
    assert f"**Last Updated:** {today} (rev4)" in state_content

    # Verify BACKLOG was updated
    backlog_content = backlog_path.read_text(encoding="utf-8")
    today = datetime.now().strftime("%Y-%m-%d")
    assert "[x] **Fix test debt**" in backlog_content
    assert f"**Last Updated:** {today}" in backlog_content


def test_update_graceful_on_missing_files(tmp_path: Path) -> None:
    """Test that updates gracefully handle missing files."""
    from runtime.tools.workflow_pack import update_state_and_backlog

    result = update_state_and_backlog(
        repo_root=tmp_path,
        branch="build/test",
        merge_sha="abc123",
        test_summary="",
        skip_on_error=True,
    )

    assert result["state_updated"] is False
    assert result["backlog_updated"] is False
    assert len(result["errors"]) > 0
    assert any("not found" in err.lower() for err in result["errors"])

````
