"""Workflow pack helpers for low-friction multi-agent handoffs."""

from __future__ import annotations

import json
import os
import re
import shlex
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path
from typing import Iterable, Optional, Sequence

import yaml

from runtime.orchestration.coo.backlog import (
    BacklogValidationError,
    load_backlog,
    mark_completed,
    save_backlog,
)
from runtime.tools.closure_policy import (
    classify_paths,
    get_tier_execution_policy,
)
from runtime.util.atomic_write import atomic_write_text
from scripts.workflow.git_lock_health import ensure_git_lock_health

# Import for BACKLOG parsing (will handle import error gracefully)
try:
    from recursive_kernel.backlog_parser import ItemStatus, mark_item_done, parse_backlog
except ImportError:
    parse_backlog = None
    mark_item_done = None
    ItemStatus = None


ACTIVE_WORK_RELATIVE_PATH = Path(".context/active_work.yaml")
QUALITY_MANIFEST_RELATIVE_PATH = Path("config/quality/manifest.yaml")
QUALITY_MYPY_BASELINE_RELATIVE_PATH = Path("config/quality/mypy_baseline.json")

QUALITY_TOOL_EXECUTABLES = {
    "ruff_check": "ruff",
    "ruff_format": "ruff",
    "mypy": "mypy",
    "biome": "biome",
    "markdownlint": "markdownlint",
    "yamllint": "yamllint",
    "shellcheck": "shellcheck",
    "agent_control_plane_pin": "python3",
}
QUALITY_PYTHON_CONFIG_FILES = {"pyproject.toml", "requirements.txt", "requirements-dev.txt"}
QUALITY_BIOME_EXTENSIONS = {".js", ".jsx", ".ts", ".tsx", ".json", ".jsonc"}
QUALITY_BIOME_CONFIG_FILES = {"biome.json"}
QUALITY_MARKDOWN_CONFIG_FILES = {".markdownlint.json", ".markdownlint.yaml", ".markdownlint.yml"}
QUALITY_YAML_CONFIG_FILES = {".yamllint", ".yamllint.yml", ".yamllint.yaml"}
QUALITY_AGENT_CONTROL_PLANE_PIN_FILES = {
    "config/external_contracts/agent_control_plane_pin.yaml",
    "scripts/workflow/check_agent_control_plane_pin.py",
}
BACKLOG_METADATA_CONTINUATION_PATTERN = re.compile(
    r"^\s+[—-]+\s*(?:DoD|Why\s*Now|Owner|Context):",
    re.IGNORECASE,
)


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


def _flatten_backlog_metadata_continuations(content: str) -> str:
    """Join wrapped backlog metadata lines onto the preceding dispatch item."""
    if not content:
        return content

    flattened: list[str] = []
    for line in content.splitlines():
        if (
            BACKLOG_METADATA_CONTINUATION_PATTERN.match(line)
            and flattened
            and flattened[-1].lstrip().startswith("- [")
        ):
            flattened[-1] = f"{flattened[-1].rstrip()} {line.strip()}"
            continue
        flattened.append(line)

    normalized = "\n".join(flattened)
    if content.endswith("\n"):
        normalized += "\n"
    return normalized


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
        normalized_findings.append({"id": finding_id, "severity": severity, "status": status})

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


def load_quality_manifest(repo_root: Path) -> dict:
    """Load the canonical quality manifest."""
    manifest_path = Path(repo_root) / QUALITY_MANIFEST_RELATIVE_PATH
    if not manifest_path.exists():
        raise FileNotFoundError(f"quality manifest not found: {manifest_path}")
    loaded = yaml.safe_load(manifest_path.read_text(encoding="utf-8")) or {}
    if not isinstance(loaded, dict):
        raise ValueError("quality manifest must be a mapping")
    return loaded


def load_mypy_baseline(repo_root: Path) -> dict:
    """Load the committed mypy baseline artifact."""
    baseline_path = Path(repo_root) / QUALITY_MYPY_BASELINE_RELATIVE_PATH
    if not baseline_path.exists():
        raise FileNotFoundError(f"mypy baseline not found: {baseline_path}")
    loaded = json.loads(baseline_path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise ValueError("mypy baseline must be a JSON object")
    return loaded


def _git_tracked_files(repo_root: Path) -> list[str]:
    proc = subprocess.run(
        ["git", "-C", str(repo_root), "ls-files"],
        check=False,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        return []
    return [line.strip() for line in proc.stdout.splitlines() if line.strip()]


def _tracked_files_matching(repo_root: Path, predicate) -> list[str]:
    return [file_path for file_path in _git_tracked_files(repo_root) if predicate(file_path)]


def _filter_quality_scope_files(files: Sequence[str], manifest: dict) -> list[str]:
    exclude_prefixes = manifest.get("repo", {}).get("exclude_prefixes", []) or []
    filtered = []
    for file_path in _unique_ordered(files):
        if any(file_path.startswith(prefix) for prefix in exclude_prefixes):
            continue
        filtered.append(file_path)
    return filtered


def _resolve_quality_scope_files(
    repo_root: Path,
    changed_files: Sequence[str],
    manifest: dict,
    scope: str,
) -> list[str]:
    if scope == "repo":
        files = _git_tracked_files(repo_root)
    else:
        files = list(changed_files)
    return _filter_quality_scope_files(files, manifest)


def route_quality_tools(
    repo_root: Path, changed_files: Sequence[str], scope: str = "changed"
) -> dict[str, list[str]]:
    """Map files to quality tools using the canonical manifest-driven router."""
    manifest = load_quality_manifest(repo_root)
    files = _resolve_quality_scope_files(repo_root, changed_files, manifest, scope)
    routed = {name: [] for name in manifest.get("tools", {})}

    python_files: list[str] = []
    python_trigger = False
    biome_files: list[str] = []
    biome_trigger = False
    markdown_files: list[str] = []
    markdown_trigger = False
    yaml_files: list[str] = []
    yaml_trigger = False
    shell_files: list[str] = []
    agent_control_plane_pin_files: list[str] = []
    agent_control_plane_pin_trigger = False

    for file_path in files:
        path = Path(file_path)
        name = path.name
        suffix = path.suffix.lower()

        if suffix == ".py":
            python_files.append(file_path)
            python_trigger = True
        elif name in QUALITY_PYTHON_CONFIG_FILES:
            python_trigger = True

        if suffix in QUALITY_BIOME_EXTENSIONS:
            biome_files.append(file_path)
            biome_trigger = True
        elif name in QUALITY_BIOME_CONFIG_FILES:
            biome_trigger = True

        # Style-only markdown checks live here; semantic doc validation stays in doc stewardship.
        if suffix == ".md" and file_path.startswith("docs/"):
            markdown_files.append(file_path)
            markdown_trigger = True
        elif name in QUALITY_MARKDOWN_CONFIG_FILES:
            markdown_trigger = True

        if name in QUALITY_YAML_CONFIG_FILES:
            yaml_trigger = True
        elif suffix in {".yml", ".yaml"}:
            yaml_files.append(file_path)
            yaml_trigger = True

        if suffix == ".sh":
            shell_files.append(file_path)

        if file_path in QUALITY_AGENT_CONTROL_PLANE_PIN_FILES:
            agent_control_plane_pin_files.append(file_path)
            agent_control_plane_pin_trigger = True

    if python_trigger:
        routed["ruff_check"] = _unique_ordered(python_files)
        routed["ruff_format"] = _unique_ordered(python_files)
        routed["mypy"] = _unique_ordered(python_files)
    if biome_trigger:
        routed["biome"] = _unique_ordered(biome_files)
    if markdown_trigger and markdown_files:
        routed["markdownlint"] = _unique_ordered(markdown_files)
    if yaml_trigger and yaml_files:
        routed["yamllint"] = _unique_ordered(yaml_files)
    if shell_files:
        routed["shellcheck"] = _unique_ordered(shell_files)
    if agent_control_plane_pin_trigger and "agent_control_plane_pin" in routed:
        routed["agent_control_plane_pin"] = _unique_ordered(agent_control_plane_pin_files)

    return routed


def _quality_tool_mode(manifest: dict, tool_name: str) -> str:
    return str(manifest.get("tools", {}).get(tool_name, {}).get("mode", "blocking"))


def _quality_tool_enabled(manifest: dict, tool_name: str, scope: str) -> bool:
    tool_cfg = manifest.get("tools", {}).get(tool_name, {})
    return bool(tool_cfg.get("enabled")) and scope in (tool_cfg.get("scopes") or [])


def _waiver_applies_to_files(paths: Sequence[str], files: Sequence[str]) -> bool:
    if not paths:
        return True
    for file_path in files:
        for candidate in paths:
            if file_path == candidate or file_path.startswith(candidate.rstrip("/") + "/"):
                return True
    return False


def _waiver_is_active(waiver: dict) -> bool:
    expires_at = str(waiver.get("expires_at", "")).strip()
    if not expires_at:
        return True
    try:
        expires = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
    except ValueError:
        return False
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    return expires >= datetime.now(timezone.utc)


def _resolve_quality_result_mode(
    manifest: dict,
    tool_name: str,
    failure_class: str,
    files: Sequence[str],
    passed: bool,
    details: str,
    *,
    scope: str,
    missing_executable: bool,
) -> tuple[str, bool, str | None]:
    mode = _quality_tool_mode(manifest, tool_name)
    if passed:
        return mode, False, None

    if missing_executable and scope == "changed":
        return "advisory", False, "tool_unavailable_locally"

    waivers = manifest.get("waivers") or []
    for waiver in waivers:
        if not isinstance(waiver, dict):
            continue
        if not _waiver_is_active(waiver):
            continue
        if waiver.get("tool") not in (None, "", tool_name):
            continue
        if waiver.get("failure_class") not in (None, "", failure_class):
            continue
        waiver_paths = waiver.get("paths") or []
        if not _waiver_applies_to_files(waiver_paths, files):
            continue
        return "advisory", True, str(waiver.get("reason", "")).strip() or None

    return mode, False, None


def _build_quality_command(
    repo_root: Path,
    manifest: dict,
    tool_name: str,
    files: Sequence[str],
    scope: str,
    fix: bool = False,
) -> list[str] | None:
    repo_config = manifest.get("repo", {})
    python_targets = repo_config.get("python_targets") or []
    markdown_config = Path(repo_root) / ".markdownlint.json"
    yamllint_config = Path(repo_root) / ".yamllint.yml"

    if tool_name == "ruff_check":
        targets = list(files) if files else (list(python_targets) if scope == "repo" else [])
        if not targets:
            return None
        cmd = ["ruff", "check"]
        if fix:
            cmd.append("--fix")
        cmd.extend(targets)
        return cmd

    if tool_name == "ruff_format":
        targets = list(files) if files else (list(python_targets) if scope == "repo" else [])
        if not targets:
            return None
        cmd = ["ruff", "format"]
        if not fix:
            cmd.append("--check")
        cmd.extend(targets)
        return cmd

    if tool_name == "mypy":
        targets = list(files) if files else (list(python_targets) if scope == "repo" else [])
        if not targets:
            return None
        return ["mypy", *targets]

    if tool_name == "biome":
        targets = list(files) if files else (["."] if scope == "repo" else [])
        if not targets:
            return None
        cmd = ["biome", "check"]
        if fix:
            cmd.append("--write")
        cmd.extend(targets)
        return cmd

    if tool_name == "markdownlint":
        if not files:
            return None
        cmd = ["markdownlint"]
        if fix:
            cmd.append("--fix")
        if markdown_config.exists():
            cmd.extend(["--config", str(markdown_config)])
        cmd.extend(files)
        return cmd

    if tool_name == "yamllint":
        if not files:
            return None
        cmd = ["yamllint"]
        if yamllint_config.exists():
            cmd.extend(["-c", str(yamllint_config)])
        cmd.extend(files)
        return cmd

    if tool_name == "shellcheck":
        if not files:
            return None
        return ["shellcheck", *files]

    if tool_name == "agent_control_plane_pin":
        manifest_path = Path("config/external_contracts/agent_control_plane_pin.yaml")
        script_path = Path("scripts/workflow/check_agent_control_plane_pin.py")
        if scope != "repo" and not files:
            return None
        if not (Path(repo_root) / manifest_path).exists():
            return None
        if not (Path(repo_root) / script_path).exists():
            return None
        return [sys.executable, str(script_path), "--manifest", str(manifest_path)]

    return None


def run_quality_gates(
    repo_root: Path,
    changed_files: Sequence[str],
    scope: str = "changed",
    fix: bool = False,
    tool_names: Sequence[str] | None = None,
) -> dict:
    """Run manifest-driven code quality gates."""
    effective_changed_files = list(changed_files)
    if scope == "changed" and not effective_changed_files:
        effective_changed_files = discover_changed_files(repo_root)

    manifest = load_quality_manifest(repo_root)
    routed = route_quality_tools(repo_root, effective_changed_files, scope=scope)
    commands_run: list[str] = []
    results: list[dict[str, object]] = []
    auto_fixed = False

    allowed_tools = set(tool_names or [])
    for tool_name in manifest.get("tools", {}):
        if allowed_tools and tool_name not in allowed_tools:
            continue
        if not _quality_tool_enabled(manifest, tool_name, scope):
            continue
        tool_cfg = manifest["tools"][tool_name]
        if fix and not tool_cfg.get("autofix_allowed"):
            continue

        files = routed.get(tool_name, [])
        command = _build_quality_command(
            repo_root,
            manifest,
            tool_name,
            files,
            scope=scope,
            fix=fix,
        )
        if not command:
            continue

        commands_run.append(shlex.join(command))
        try:
            proc = subprocess.run(
                command,
                check=False,
                cwd=Path(repo_root),
                capture_output=True,
                text=True,
            )
            passed = proc.returncode == 0
            details = (proc.stderr or "").strip() or (proc.stdout or "").strip()
            missing_executable = False
        except FileNotFoundError as exc:
            passed = False
            details = str(exc)
            missing_executable = True

        result = {
            "tool": tool_name,
            "failure_class": str(tool_cfg.get("failure_class", "quality_error")),
            "passed": passed,
            "auto_fixed": bool(fix and tool_cfg.get("autofix_allowed") and passed),
            "files": list(files),
            "details": details,
        }
        result["mode"], result["waived"], waiver_reason = _resolve_quality_result_mode(
            manifest,
            tool_name,
            str(result["failure_class"]),
            list(files),
            passed,
            details,
            scope=scope,
            missing_executable=missing_executable,
        )
        if waiver_reason:
            result["waiver_reason"] = waiver_reason
        results.append(result)
        auto_fixed = auto_fixed or bool(result["auto_fixed"])

    blocking_failures = [r for r in results if (not r["passed"]) and r["mode"] == "blocking"]
    advisory_failures = [r for r in results if (not r["passed"]) and r["mode"] == "advisory"]
    summary = (
        f"Quality gate ran {len(results)} tool(s); "
        f"{len(blocking_failures)} blocking failure(s), "
        f"{len(advisory_failures)} advisory failure(s)."
    )

    return {
        "passed": not blocking_failures,
        "scope": scope,
        "summary": summary,
        "commands_run": commands_run,
        "files_checked": _resolve_quality_scope_files(
            repo_root, effective_changed_files, manifest, scope
        ),
        "results": results,
        "auto_fixed": auto_fixed,
    }


def doctor_quality_tools(repo_root: Path) -> dict:
    """Inspect whether enabled quality tool executables are present."""
    manifest = load_quality_manifest(repo_root)
    results = []
    for tool_name in manifest.get("tools", {}):
        executable = QUALITY_TOOL_EXECUTABLES.get(tool_name, tool_name)
        present = shutil.which(executable) is not None
        results.append(
            {
                "tool": tool_name,
                "enabled": bool(manifest["tools"][tool_name].get("enabled")),
                "executable": executable,
                "present": present,
                "mode": _quality_tool_mode(manifest, tool_name),
            }
        )

    return {
        "passed": all((not row["enabled"]) or row["present"] for row in results),
        "results": results,
        "summary": f"Quality doctor inspected {len(results)} tool(s).",
    }


def route_targeted_tests(
    changed_files: Sequence[str], closure_tier: str | None = None
) -> list[str]:
    """Map changed files to targeted test commands."""
    files = _unique_ordered(changed_files)
    effective_tier = closure_tier or classify_paths(files)["closure_tier"]
    policy = get_tier_execution_policy(effective_tier)
    if not policy["run_targeted_pytest"]:
        return []
    if policy["targeted_pytest_commands"]:
        return list(policy["targeted_pytest_commands"])

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
            add("pytest -q runtime/tests/test_agent_api_usage_plumbing.py tests/test_agent_api.py")
            continue

        if _matches(
            file_path,
            (
                "runtime/tools/workflow_pack.py",
                "runtime/tests/test_workflow_pack.py",
                "runtime/tests/test_git_workflow_worktree.py",
                "scripts/workflow/",
            ),
        ):
            add(
                "pytest -q runtime/tests/test_workflow_pack.py runtime/tests/test_git_workflow_worktree.py"  # noqa: E501
            )
            continue

        if _matches(
            file_path,
            (
                "runtime/tests/test_quality_gate.py",
                "runtime/tests/test_closure_gate.py",
                "config/quality/",
            ),
        ):
            add(
                "pytest -q runtime/tests/test_quality_gate.py"
                " runtime/tests/test_closure_gate.py"
                " runtime/tests/test_workflow_pack.py"
                " runtime/tests/test_git_workflow_worktree.py"
            )
            continue

        if _matches(
            file_path,
            (
                "runtime/tools/openclaw_models_preflight.sh",
                "runtime/tools/openclaw_model_policy_assert.py",
                "runtime/tools/openclaw_policy_assert.py",
                "runtime/tools/openclaw_verify_memory.sh",
                "runtime/tools/openclaw_memory_policy_guard.py",
                "runtime/tools/openclaw_host_cron_parity_guard.py",
                "runtime/tools/openclaw_gate_reason_catalog.py",
                "runtime/tools/openclaw_promotion_state.py",
                "runtime/tools/openclaw_coo_update_protocol.sh",
                "runtime/tools/coo_worktree.sh",
                "runtime/tests/test_openclaw_model_policy_assert.py",
                "runtime/tests/test_openclaw_policy_assert.py",
                "runtime/tests/test_openclaw_memory_policy_assert.py",
                "runtime/tests/test_openclaw_memory_policy_guard.py",
                "runtime/tests/test_openclaw_memory_policy_guard_curated.py",
                "runtime/tests/test_openclaw_gate_reason_catalog.py",
                "runtime/tests/test_openclaw_host_cron_parity_guard.py",
                "runtime/tests/test_coo_worktree_breakglass.py",
                "runtime/tests/test_openclaw_promotion_state.py",
                "runtime/tests/test_openclaw_coo_update_protocol_promotion.py",
            ),
        ):
            add(
                "pytest -q runtime/tests/test_openclaw_model_policy_assert.py "
                "runtime/tests/test_openclaw_policy_assert.py "
                "runtime/tests/test_openclaw_memory_policy_assert.py "
                "runtime/tests/test_openclaw_memory_policy_guard.py "
                "runtime/tests/test_openclaw_memory_policy_guard_curated.py "
                "runtime/tests/test_openclaw_gate_reason_catalog.py "
                "runtime/tests/test_openclaw_host_cron_parity_guard.py "
                "runtime/tests/test_coo_worktree_breakglass.py "
                "runtime/tests/test_openclaw_promotion_state.py "
                "runtime/tests/test_openclaw_coo_update_protocol_promotion.py"
            )
            continue

        if _matches(file_path, ("docs/",)):
            add("pytest -q runtime/tests/test_doc_hygiene.py runtime/tests/test_backlog_parser.py")
            continue

        if _matches(
            file_path,
            (
                "scripts/wiki/",
                "doc_steward/wiki_lint_validator.py",
                "doc_steward/cli.py",
                "runtime/tests/test_wiki_lint_validator.py",
            ),
        ):
            add("pytest -q runtime/tests/test_wiki_lint_validator.py")
            continue

        if _matches(file_path, (".context/wiki/",)):
            add("pytest -q runtime/tests/test_wiki_lint_validator.py")
            continue

        if _matches(file_path, (".gitignore",)):
            continue

        if _matches(
            file_path,
            (
                "runtime/orchestration/loop/spine.py",
                "runtime/tests/test_loop_spine.py",
                "runtime/orchestration/loop/",
                "runtime/orchestration/council/shadow_runner.py",
                "runtime/tests/orchestration/council/test_shadow_runner.py",
            ),
        ):
            add(
                "pytest -q runtime/tests/test_loop_spine.py "
                "runtime/tests/orchestration/council/test_shadow_runner.py"
            )
            continue

        if _matches(
            file_path,
            (
                "pyproject.toml",
                "pytest.ini",
            ),
        ):
            add(
                "pytest -q runtime/tests/test_known_failures_gate.py runtime/tests/test_state_hygiene.py"  # noqa: E501
            )
            continue

        if _matches(file_path, ("artifacts/status/",)):
            # Regenerated artifacts — no targeted tests required; doc stewardship handles freshness
            add("pytest -q runtime/tests/test_workflow_pack.py")
            continue

        if _matches(
            file_path,
            (
                "runtime/orchestration/coo/",
                "runtime/tests/orchestration/coo/",
            ),
        ):
            add("pytest -q runtime/tests/orchestration/coo/")
            continue

        if _matches(file_path, ("config/tasks/",)):
            # Structured backlog config — validate via backlog tests
            add("pytest -q runtime/tests/orchestration/coo/test_backlog.py")
            continue

        if _matches(file_path, ("config/governance/",)):
            # Governance config (YAML only) — doc hygiene is sufficient
            add("pytest -q runtime/tests/test_doc_hygiene.py")
            continue

        if _matches(
            file_path,
            (
                "artifacts/plans/",
                "artifacts/reviews/",
                "artifacts/handoffs/",
                "artifacts/coo/",
                "artifacts/evidence/",
                "artifacts/content/",
                "artifacts/upgrades/",
            ),
        ):
            # Pure artifact files — no code impact; workflow_pack smoke is sufficient
            add("pytest -q runtime/tests/test_workflow_pack.py")
            continue

    if not routed:
        routed.append("pytest -q runtime/tests")
    return routed


def discover_changed_files(repo_root: Path, branch: str | None = None) -> list[str]:
    """Discover changed files with staged-first precedence.

    When *branch* is provided (e.g. when the hook fires on a merge command from
    main context), a ``git diff main..<branch>`` probe is prepended so the gate
    sees the branch's actual changes rather than main's recent commits.
    """
    repo = Path(repo_root)
    probes = []
    if branch:
        probes.append(["git", "-C", str(repo), "diff", "--name-only", f"main..{branch}"])
    probes.append(["git", "-C", str(repo), "status", "--short"])
    probes.extend(
        [
            ["git", "-C", str(repo), "diff", "--name-only", "--cached"],
            ["git", "-C", str(repo), "diff", "--name-only"],
            ["git", "-C", str(repo), "diff", "--name-only", "HEAD~1..HEAD"],
        ]
    )
    for cmd in probes:
        proc = subprocess.run(cmd, check=False, capture_output=True, text=True)
        if proc.returncode != 0:
            continue
        if cmd[-2:] == ["status", "--short"]:
            files = []
            for line in proc.stdout.splitlines():
                if len(line) < 4:
                    continue
                candidate = line[3:].strip()
                if " -> " in candidate:
                    candidate = candidate.split(" -> ", 1)[1].strip()
                if not candidate:
                    continue
                candidate_path = repo / candidate
                if candidate_path.is_dir():
                    for nested in sorted(candidate_path.rglob("*")):
                        if nested.is_file():
                            files.append(str(nested.relative_to(repo)).replace(os.sep, "/"))
                    continue
                files.append(candidate)
        else:
            files = [line.strip() for line in proc.stdout.splitlines() if line.strip()]
        if files:
            return _unique_ordered(files)
    return []


def run_closure_tests(
    repo_root: Path,
    changed_files: Sequence[str],
    *,
    closure_tier: str | None = None,
) -> dict:
    """Run targeted closure tests derived from changed files."""
    effective_tier = closure_tier or classify_paths(changed_files)["closure_tier"]
    if effective_tier == "no_changes":
        return {
            "passed": True,
            "commands_run": [],
            "summary": "Valid diff with zero changed paths; targeted closure tests skipped.",
            "failures": [],
            "closure_tier": effective_tier,
        }

    if not get_tier_execution_policy(effective_tier)["run_targeted_pytest"]:
        return {
            "passed": True,
            "commands_run": [],
            "summary": f"{effective_tier} change; targeted closure tests skipped.",
            "failures": [],
            "closure_tier": effective_tier,
        }

    commands = route_targeted_tests(changed_files, closure_tier=effective_tier)
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
        "closure_tier": effective_tier,
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
        path == "docs/11_admin" or path.startswith("docs/11_admin/") for path in changed_files
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

        # Admin archive link ban check — scope to changed admin doc paths
        admin_doc_paths = [
            p
            for p in changed_files
            if p.endswith(".md") and p.startswith("docs/11_admin/") and not p.endswith("/")
        ]
        admin_archive_cmd = [
            sys.executable,
            "-m",
            "doc_steward.cli",
            "admin-archive-link-ban-check",
            str(repo_root),
        ]
        if admin_doc_paths:
            admin_archive_cmd += ["--paths"] + admin_doc_paths
        admin_archive_proc = subprocess.run(
            admin_archive_cmd,
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
            [
                sys.executable,
                "-m",
                "doc_steward.cli",
                "artefact-index-check",
                str(repo_root),
                "--directory",
                "docs/02_protocols",
            ],
            check=False,
            cwd=Path(repo_root),
            capture_output=True,
            text=True,
        )
        if protocols_index_proc.returncode != 0:
            errors.append(f"Protocols artefact index check failed:\n{protocols_index_proc.stdout}")

        # Global archive link ban check — scope to changed protocol doc paths
        protocols_doc_paths = [
            p
            for p in changed_files
            if p.endswith(".md") and p.startswith("docs/02_protocols/") and not p.endswith("/")
        ]
        protocols_link_cmd = [
            sys.executable,
            "-m",
            "doc_steward.cli",
            "docs-archive-link-ban-check",
            str(repo_root),
        ]
        if protocols_doc_paths:
            protocols_link_cmd += ["--paths"] + protocols_doc_paths
        protocols_link_proc = subprocess.run(
            protocols_link_cmd,
            check=False,
            cwd=Path(repo_root),
            capture_output=True,
            text=True,
        )
        if protocols_link_proc.returncode != 0:
            errors.append(f"Archive link ban check failed:\n{protocols_link_proc.stdout}")

    # Check if docs/03_runtime/ files changed -> run runtime validators
    runtime_changed = any(
        path == "docs/03_runtime" or path.startswith("docs/03_runtime/") for path in changed_files
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
            [
                sys.executable,
                "-m",
                "doc_steward.cli",
                "artefact-index-check",
                str(repo_root),
                "--directory",
                "docs/03_runtime",
            ],
            check=False,
            cwd=Path(repo_root),
            capture_output=True,
            text=True,
        )
        if runtime_index_proc.returncode != 0:
            errors.append(f"Runtime artefact index check failed:\n{runtime_index_proc.stdout}")

        # Global archive link ban check — scope to changed runtime doc paths
        runtime_doc_paths = [
            p
            for p in changed_files
            if p.endswith(".md") and p.startswith("docs/03_runtime/") and not p.endswith("/")
        ]
        runtime_link_cmd = [
            sys.executable,
            "-m",
            "doc_steward.cli",
            "docs-archive-link-ban-check",
            str(repo_root),
        ]
        if runtime_doc_paths:
            runtime_link_cmd += ["--paths"] + runtime_doc_paths
        runtime_link_proc = subprocess.run(
            runtime_link_cmd,
            check=False,
            cwd=Path(repo_root),
            capture_output=True,
            text=True,
        )
        if runtime_link_proc.returncode != 0:
            errors.append(f"Archive link ban check failed:\n{runtime_link_proc.stdout}")

    # Check if docs/99_archive/ files changed -> run archive validators
    archive_changed = any(
        path == "docs/99_archive" or path.startswith("docs/99_archive/") for path in changed_files
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


def merge_to_main(repo_root: Path, branch: str, allow_concurrent_wip: bool = False) -> dict:
    """Merge a feature branch into main using squash merge."""
    source_branch = branch.strip()
    if not source_branch:
        return {
            "success": False,
            "merge_sha": None,
            "primary_repo": None,
            "errors": ["source branch is empty"],
        }
    if source_branch in {"main", "master"}:
        return {
            "success": False,
            "merge_sha": None,
            "primary_repo": None,
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
            "primary_repo": None,
            "errors": [f"safety gate blocked merge: {details or 'unknown failure'}"],
        }

    # Find the primary worktree — when running from a linked git worktree,
    # checkout/merge must target the primary repo where main is checked out.
    # Scanning git worktree list --porcelain to find the entry whose branch is main.
    _wt_proc = subprocess.run(
        ["git", "-C", str(repo), "worktree", "list", "--porcelain"],
        check=False,
        capture_output=True,
        text=True,
    )
    primary_repo: Path = repo
    _candidate: Path = repo
    for _line in _wt_proc.stdout.splitlines():
        if _line.startswith("worktree "):
            _candidate = Path(_line.split(" ", 1)[1].strip())
        elif _line.startswith("branch refs/heads/"):
            _branch_name = _line.removeprefix("branch refs/heads/").strip()
            if _branch_name in {"main", "master"}:
                primary_repo = _candidate
                break

    _primary_head_proc = subprocess.run(
        ["git", "-C", str(primary_repo), "branch", "--show-current"],
        check=False,
        capture_output=True,
        text=True,
    )
    _repo_already_on_main = _primary_head_proc.stdout.strip() in {"main", "master"}

    # Gate: fail early if the primary repo has untracked files.
    # The pre-commit hook (Article XIX) unconditionally blocks commits when
    # untracked files exist, even with LIFEOS_MAIN_COMMIT_ALLOWED=1.
    # Catching this before `git merge --squash` prevents orphaned staged changes.
    # Pass allow_concurrent_wip=True to skip this gate when concurrent agent
    # WIP is intentionally present in the primary repo (Article XIX chicken-and-egg).
    if not allow_concurrent_wip:
        _untracked_proc = subprocess.run(
            ["git", "-C", str(primary_repo), "ls-files", "--others", "--exclude-standard"],
            check=False,
            capture_output=True,
            text=True,
        )
        _untracked = _untracked_proc.stdout.strip()
        if _untracked:
            _untracked_list = _untracked.splitlines()
            errors.append(
                f"primary repo has {len(_untracked_list)} untracked file(s) — "
                "Article XIX will block the merge commit. "
                "Stage, gitignore, or remove them before retrying: "
                + ", ".join(_untracked_list[:5])
                + ("..." if len(_untracked_list) > 5 else "")
            )
            return {
                "success": False,
                "merge_sha": None,
                "primary_repo": str(primary_repo),
                "errors": errors,
            }

    lock_health = ensure_git_lock_health(primary_repo, auto_cleanup=True)
    if lock_health.removed_locks:
        errors.append(
            "Git lock recovery: removed orphaned lock(s): " + ", ".join(lock_health.removed_locks)
        )
    if not lock_health.ok:
        details = " | ".join(lock_health.notes) if lock_health.notes else "unknown git lock owner"
        errors.append(
            "Git lock blocker: " + ", ".join(lock_health.blocking_locks) + f" | {details}"
        )
        return {
            "success": False,
            "merge_sha": None,
            "primary_repo": str(primary_repo),
            "errors": errors,
        }

    steps = [
        *(
            [("checkout main", ["git", "-C", str(primary_repo), "checkout", "main"])]
            if not _repo_already_on_main
            else []
        ),
        ("pull --ff-only", ["git", "-C", str(primary_repo), "pull", "--ff-only"]),
        ("squash merge", ["git", "-C", str(primary_repo), "merge", "--squash", source_branch]),
        (
            "commit squash merge",
            [
                "git",
                "-C",
                str(primary_repo),
                "commit",
                *(["--no-verify"] if allow_concurrent_wip else []),
                "-m",
                f"feat: Merge {source_branch} (squashed)"
                + (
                    "\n\n--no-verify: Article XIX chicken-and-egg exemption. "
                    "Concurrent agent WIP present in primary repo (allow_concurrent_wip=True)."
                    if allow_concurrent_wip
                    else ""
                ),
            ],
        ),
    ]

    for label, cmd in steps:
        step_lock_health = ensure_git_lock_health(primary_repo, auto_cleanup=True)
        if step_lock_health.removed_locks:
            errors.append(
                "Git lock recovery: removed orphaned lock(s): "
                + ", ".join(step_lock_health.removed_locks)
            )
        if not step_lock_health.ok:
            details = (
                " | ".join(step_lock_health.notes)
                if step_lock_health.notes
                else "unknown git lock owner"
            )
            errors.append(
                f"{label} blocked by Git lock: "
                + ", ".join(step_lock_health.blocking_locks)
                + f" | {details}"
            )
            return {
                "success": False,
                "merge_sha": None,
                "primary_repo": str(primary_repo),
                "errors": errors,
            }
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
        after_failure_lock_health = ensure_git_lock_health(primary_repo, auto_cleanup=False)
        if after_failure_lock_health.blocking_locks:
            lock_details = (
                " | ".join(after_failure_lock_health.notes)
                if after_failure_lock_health.notes
                else "unknown git lock owner"
            )
            errors.append(
                "Git lock blocker: "
                + ", ".join(after_failure_lock_health.blocking_locks)
                + f" | {lock_details}"
            )
        # If the squash merge staged changes into the index, reset to unstage
        # them before switching branches.  Without this, orphaned staged
        # changes persist on main, contaminating future operations.
        if label in ("squash merge", "commit squash merge"):
            subprocess.run(
                ["git", "-C", str(primary_repo), "reset", "HEAD"],
                check=False,
                capture_output=True,
                text=True,
            )
        subprocess.run(
            ["git", "-C", str(primary_repo), "checkout", source_branch],
            check=False,
            capture_output=True,
            text=True,
        )
        return {
            "success": False,
            "merge_sha": None,
            "primary_repo": str(primary_repo),
            "errors": errors,
        }

    head = subprocess.run(
        ["git", "-C", str(primary_repo), "rev-parse", "HEAD"],
        check=False,
        capture_output=True,
        text=True,
    )
    merge_sha = head.stdout.strip() if head.returncode == 0 else None
    if not merge_sha:
        errors.append("failed to resolve merge commit SHA")
        return {
            "success": False,
            "merge_sha": None,
            "primary_repo": None,
            "errors": errors,
        }

    # Post-merge health check: verify primary repo is clean.
    _health_proc = subprocess.run(
        ["git", "-C", str(primary_repo), "status", "--porcelain"],
        check=False,
        capture_output=True,
        text=True,
    )
    _health_output = _health_proc.stdout.strip()
    if _health_output:
        _dirty_count = len(_health_output.splitlines())
        errors.append(
            f"post-merge health check: primary repo has {_dirty_count} dirty file(s) — "
            "this may indicate a merge artifact or concurrent agent conflict"
        )

    return {
        "success": True,
        "merge_sha": merge_sha,
        "primary_repo": str(primary_repo),
        "errors": errors,
    }


def cleanup_after_merge(repo_root: Path, branch: str, clear_context: bool = True) -> dict:
    """Cleanup local branch and active context artifact after merge."""
    repo = Path(repo_root)
    source_branch = branch.strip()

    errors: list[str] = []

    # Eagerly import before worktree removal destroys CWD.
    _gw = None
    try:
        from scripts import git_workflow as _gw
    except Exception:
        pass

    _wt_proc = subprocess.run(
        ["git", "-C", str(repo), "worktree", "list", "--porcelain"],
        check=False,
        capture_output=True,
        text=True,
    )
    primary_repo: Optional[Path] = None
    linked_wt_path: Optional[Path] = None
    candidate: Optional[Path] = None
    for line in _wt_proc.stdout.splitlines():
        if line.startswith("worktree "):
            candidate = Path(line.split(" ", 1)[1].strip())
        elif line.startswith("branch refs/heads/") and candidate is not None:
            wt_branch = line.removeprefix("branch refs/heads/").strip()
            if wt_branch in {"main", "master"} and primary_repo is None:
                primary_repo = candidate
            elif wt_branch == source_branch and linked_wt_path is None:
                linked_wt_path = candidate

    worktree_removed = False
    if linked_wt_path is not None and linked_wt_path != primary_repo:
        git_cwd = str(primary_repo) if primary_repo is not None else str(repo)
        target_repo = primary_repo if primary_repo is not None else repo
        lock_health = ensure_git_lock_health(target_repo, auto_cleanup=True)
        if not lock_health.ok:
            details = (
                " | ".join(lock_health.notes) if lock_health.notes else "unknown git lock owner"
            )
            errors.append(
                "Git lock blocker: " + ", ".join(lock_health.blocking_locks) + f" | {details}"
            )
            return {
                "branch_deleted": False,
                "context_cleared": False,
                "worktree_removed": False,
                "registry_records_closed": 0,
                "errors": errors,
            }
        rm_proc = subprocess.run(
            ["git", "-C", git_cwd, "worktree", "remove", "--force", str(linked_wt_path)],
            check=False,
            capture_output=True,
            text=True,
        )
        if rm_proc.returncode == 0:
            worktree_removed = True
        else:
            details = (rm_proc.stderr or "").strip() or (rm_proc.stdout or "").strip()
            errors.append(
                f"failed to remove worktree at {linked_wt_path}: {details or f'exit code {rm_proc.returncode}'}"  # noqa: E501
            )

    branch_delete_repo = primary_repo if primary_repo is not None else repo
    branch_deleted = False
    registry_records_closed = 0
    if source_branch and source_branch not in {"main", "master"}:
        lock_health = ensure_git_lock_health(branch_delete_repo, auto_cleanup=True)
        if not lock_health.ok:
            details = (
                " | ".join(lock_health.notes) if lock_health.notes else "unknown git lock owner"
            )
            errors.append(
                "Git lock blocker: " + ", ".join(lock_health.blocking_locks) + f" | {details}"
            )
            return {
                "branch_deleted": False,
                "context_cleared": False,
                "worktree_removed": worktree_removed,
                "registry_records_closed": 0,
                "errors": errors,
            }
        proc = subprocess.run(
            ["git", "-C", str(branch_delete_repo), "branch", "-D", source_branch],
            check=False,
            capture_output=True,
            text=True,
        )
        if proc.returncode == 0:
            branch_deleted = True
        else:
            details = (proc.stderr or "").strip() or (proc.stdout or "").strip()
            errors.append(
                f"failed to delete local branch '{source_branch}': {details or f'exit code {proc.returncode}'}"  # noqa: E501
            )

        if _gw is not None:
            try:
                registry_result = _gw.close_active_branch_records(
                    source_branch,
                    repo_root=branch_delete_repo,
                    worktree_path=str(linked_wt_path) if linked_wt_path is not None else None,
                )
                registry_records_closed = int(registry_result.get("updated", 0))
            except Exception as exc:
                errors.append(f"failed to update active_branches.json: {exc}")

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
        "worktree_removed": worktree_removed,
        "registry_records_closed": registry_records_closed,
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
            updated_content[:insert_pos] + new_win_entry + updated_content[insert_pos:]
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
        updated_content = _flatten_backlog_metadata_continuations(updated_content)
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
        commit_messages = [line.strip() for line in proc.stdout.splitlines() if line.strip()]

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


def update_structured_backlog(
    repo_root: Path,
    merge_sha: str,
    skip_on_error: bool = True,
) -> dict:
    """
    Mark completed tasks in config/tasks/backlog.yaml based on recently
    completed ExecutionOrders in artifacts/dispatch/completed/.

    Scans completed orders for task_ref values, then marks matching backlog
    tasks as completed if they are currently in_progress or pending.

    Returns:
        dict with keys:
            - updated (bool): at least one task was marked completed
            - tasks_completed (list[str]): task IDs that were marked
            - errors (list[str]): any warnings/errors (non-fatal if skip_on_error)
    """
    repo_root = Path(repo_root)
    errors: list[str] = []
    tasks_completed: list[str] = []

    backlog_path = repo_root / "config" / "tasks" / "backlog.yaml"
    if not backlog_path.exists():
        return {
            "updated": False,
            "tasks_completed": [],
            "errors": ["backlog.yaml not found"],
        }

    try:
        tasks = load_backlog(backlog_path)
    except BacklogValidationError as exc:
        return {
            "updated": False,
            "tasks_completed": [],
            "errors": [f"invalid backlog.yaml: {exc}"],
        }
    except Exception as exc:  # pragma: no cover - defensive guard
        msg = f"failed to load backlog.yaml: {exc}"
        if skip_on_error:
            return {"updated": False, "tasks_completed": [], "errors": [msg]}
        raise

    completed_dir = repo_root / "artifacts" / "dispatch" / "completed"
    if not completed_dir.exists():
        return {"updated": False, "tasks_completed": [], "errors": errors}

    task_refs: set[str] = set()
    try:
        order_files = sorted(completed_dir.glob("*.yaml"))
    except Exception as exc:  # pragma: no cover - defensive guard
        msg = f"failed to scan completed orders: {exc}"
        if skip_on_error:
            errors.append(msg)
            return {"updated": False, "tasks_completed": [], "errors": errors}
        raise

    for order_path in order_files:
        try:
            order = yaml.safe_load(order_path.read_text(encoding="utf-8"))
        except Exception as exc:
            msg = f"failed to read completed order '{order_path.name}': {exc}"
            if skip_on_error:
                errors.append(msg)
                continue
            raise

        if not isinstance(order, dict):
            msg = f"completed order '{order_path.name}' must be a YAML mapping"
            if skip_on_error:
                errors.append(msg)
                continue
            raise ValueError(msg)

        outcome = order.get("outcome")
        if outcome is None:
            errors.append(f"completed order '{order_path.name}' missing outcome; skipped")
            continue

        if str(outcome).strip().upper() != "SUCCESS":
            continue

        task_ref = str(order.get("task_ref", "")).strip()
        if task_ref:
            task_refs.add(task_ref)

    for task_ref in sorted(task_refs):
        try:
            task = next((entry for entry in tasks if entry.id == task_ref), None)
            if task is None:
                continue
            if task.status not in ("pending", "in_progress"):
                continue
            tasks = mark_completed(tasks, task_ref, evidence=f"merge:{merge_sha}")
            tasks_completed.append(task_ref)
        except Exception as exc:
            msg = f"failed to mark task '{task_ref}' complete: {exc}"
            if skip_on_error:
                errors.append(msg)
                continue
            raise

    if tasks_completed:
        try:
            save_backlog(backlog_path, tasks)
        except Exception as exc:
            msg = f"failed to save backlog.yaml: {exc}"
            if skip_on_error:
                errors.append(msg)
            else:
                raise

    return {
        "updated": bool(tasks_completed),
        "tasks_completed": tasks_completed,
        "errors": errors,
    }
