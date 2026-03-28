#!/usr/bin/env python3
"""Run the LifeOS repo-wide quality baseline audit."""

from __future__ import annotations

import argparse
import filecmp
import json
import os
import shlex
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


SCRIPT_PATH = Path(__file__).resolve()
REPO_ROOT = SCRIPT_PATH.parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from runtime.tools.workflow_pack import load_quality_manifest  # noqa: E402


REPORT_DIR_REL = Path("artifacts/reports/quality_audit_baseline_v1")
SUMMARY_REL = Path("docs/11_admin/QUALITY_AUDIT_BASELINE_v1.0.md")
TECH_DEBT_REL = Path("docs/11_admin/TECH_DEBT_INVENTORY.md")
DOCS_INDEX_REL = Path("docs/INDEX.md")
PYTHON_EXE = shlex.quote(sys.executable)


@dataclass(frozen=True)
class CommandSpec:
    artifact_name: str
    lane: str
    tool: str
    failure_class: str
    subsystem: str
    command: str
    notes: str = ""


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def utc_date() -> str:
    return utc_now().date().isoformat()


def utc_timestamp() -> str:
    return utc_now().isoformat().replace("+00:00", "Z")


def _shell(command: str) -> list[str]:
    return ["/bin/bash", "-lc", command]


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def append_exit_footer(content: str, *, exit_code: int, timeout_seconds: int | None = None) -> str:
    updated = content
    if updated and not updated.endswith("\n"):
        updated += "\n"
    if timeout_seconds is not None:
        updated += f"TIMEOUT_SECONDS={timeout_seconds}\n"
    updated += f"EXIT_CODE={exit_code}\n"
    return updated


def capture_command(repo_root: Path, command: str, output_path: Path, *, timeout_seconds: int = 300) -> dict:
    try:
        proc = subprocess.run(
            _shell(command),
            cwd=repo_root,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired as exc:
        partial = (exc.stdout or "") + (exc.stderr or "")
        if output_path.exists():
            partial = output_path.read_text(encoding="utf-8")
        partial = append_exit_footer(partial, exit_code=124, timeout_seconds=timeout_seconds)
        _write_text(output_path, partial)
        return {
            "command": command,
            "output_path": str(output_path.relative_to(repo_root)),
            "exit_code": 124,
            "output": partial,
        }
    if output_path.exists():
        combined = output_path.read_text(encoding="utf-8")
        if extract_exit_code(combined) is None:
            combined = append_exit_footer(combined, exit_code=proc.returncode)
            _write_text(output_path, combined)
    else:
        combined = (proc.stdout or "") + (proc.stderr or "")
        combined = append_exit_footer(combined, exit_code=proc.returncode)
        _write_text(output_path, combined)
    return {
        "command": command,
        "output_path": str(output_path.relative_to(repo_root)),
        "exit_code": proc.returncode,
        "output": combined,
    }


def capture_json_command(repo_root: Path, command: str, output_path: Path, *, timeout_seconds: int = 300) -> dict:
    try:
        proc = subprocess.run(
            _shell(command),
            cwd=repo_root,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired:
        payload = {
            "passed": False,
            "timed_out": True,
            "summary": f"command timed out after {timeout_seconds} second(s)",
            "results": [],
            "commands_run": [],
            "files_checked": [],
            "auto_fixed": False,
        }
        _write_text(output_path, json.dumps(payload, indent=2, sort_keys=True) + "\n")
        return payload
    stdout = proc.stdout or ""
    stderr = proc.stderr or ""
    if proc.returncode != 0 and stderr:
        raise RuntimeError(f"command failed: {command}\n{stderr}")
    payload = json.loads(stdout)
    _write_text(output_path, json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return payload


def audit_command_specs(report_dir: Path) -> list[CommandSpec]:
    return [
        CommandSpec(
            artifact_name="ruff_check_python.txt",
            lane="python_style",
            tool="ruff_check",
            failure_class="ruff_error",
            subsystem="runtime+doc_steward+recursive_kernel+project_builder",
            command=(
                "ruff check runtime doc_steward recursive_kernel project_builder"
                f" > {report_dir / 'ruff_check_python.txt'} 2>&1; "
                f"code=$?; printf '\\nEXIT_CODE=%s\\n' \"$code\" >> {report_dir / 'ruff_check_python.txt'}; exit 0"
            ),
        ),
        CommandSpec(
            artifact_name="ruff_format_python.txt",
            lane="python_format",
            tool="ruff_format",
            failure_class="ruff_error",
            subsystem="runtime+doc_steward+recursive_kernel+project_builder",
            command=(
                "ruff format --check runtime doc_steward recursive_kernel project_builder"
                f" > {report_dir / 'ruff_format_python.txt'} 2>&1; "
                f"code=$?; printf '\\nEXIT_CODE=%s\\n' \"$code\" >> {report_dir / 'ruff_format_python.txt'}; exit 0"
            ),
        ),
        CommandSpec(
            artifact_name="mypy_python.txt",
            lane="python_types",
            tool="mypy",
            failure_class="mypy_error",
            subsystem="runtime+doc_steward+recursive_kernel+project_builder",
            command=(
                "mypy runtime doc_steward recursive_kernel project_builder"
                f" > {report_dir / 'mypy_python.txt'} 2>&1; "
                f"code=$?; printf '\\nEXIT_CODE=%s\\n' \"$code\" >> {report_dir / 'mypy_python.txt'}; exit 0"
            ),
        ),
        CommandSpec(
            artifact_name="ruff_check_opencode_governance.txt",
            lane="python_style",
            tool="ruff_check",
            failure_class="ruff_error",
            subsystem="opencode_governance",
            command=(
                "ruff check opencode_governance"
                f" > {report_dir / 'ruff_check_opencode_governance.txt'} 2>&1; "
                f"code=$?; printf '\\nEXIT_CODE=%s\\n' \"$code\" >> {report_dir / 'ruff_check_opencode_governance.txt'}; exit 0"
            ),
            notes="packaged_but_not_in_manifest",
        ),
        CommandSpec(
            artifact_name="ruff_format_opencode_governance.txt",
            lane="python_format",
            tool="ruff_format",
            failure_class="ruff_error",
            subsystem="opencode_governance",
            command=(
                "ruff format --check opencode_governance"
                f" > {report_dir / 'ruff_format_opencode_governance.txt'} 2>&1; "
                f"code=$?; printf '\\nEXIT_CODE=%s\\n' \"$code\" >> {report_dir / 'ruff_format_opencode_governance.txt'}; exit 0"
            ),
            notes="packaged_but_not_in_manifest",
        ),
        CommandSpec(
            artifact_name="mypy_opencode_governance.txt",
            lane="python_types",
            tool="mypy",
            failure_class="mypy_error",
            subsystem="opencode_governance",
            command=(
                "mypy opencode_governance"
                f" > {report_dir / 'mypy_opencode_governance.txt'} 2>&1; "
                f"code=$?; printf '\\nEXIT_CODE=%s\\n' \"$code\" >> {report_dir / 'mypy_opencode_governance.txt'}; exit 0"
            ),
            notes="packaged_but_not_in_manifest",
        ),
        CommandSpec(
            artifact_name="biome_repo.txt",
            lane="js_json_style",
            tool="biome",
            failure_class="biome_error",
            subsystem="scripts_root_config",
            command=(
                "biome check ."
                f" > {report_dir / 'biome_repo.txt'} 2>&1; "
                f"code=$?; printf '\\nEXIT_CODE=%s\\n' \"$code\" >> {report_dir / 'biome_repo.txt'}; exit 0"
            ),
            notes="broader_than_quality_gate_routing",
        ),
        CommandSpec(
            artifact_name="markdownlint_docs.txt",
            lane="docs_markdown_style",
            tool="markdownlint",
            failure_class="markdownlint_error",
            subsystem="docs_markdown_style",
            command=(
                "git ls-files 'docs/*.md' 'docs/**/*.md' | "
                "xargs -r markdownlint --config .markdownlint.json"
                f" > {report_dir / 'markdownlint_docs.txt'} 2>&1; "
                f"code=$?; printf '\\nEXIT_CODE=%s\\n' \"$code\" >> {report_dir / 'markdownlint_docs.txt'}; exit 0"
            ),
        ),
        CommandSpec(
            artifact_name="yamllint_repo.txt",
            lane="yaml_style",
            tool="yamllint",
            failure_class="yamllint_error",
            subsystem="yaml_shell_json_misc",
            command=(
                "git ls-files '*.yml' '*.yaml' | xargs -r yamllint -c .yamllint.yml"
                f" > {report_dir / 'yamllint_repo.txt'} 2>&1; "
                f"code=$?; printf '\\nEXIT_CODE=%s\\n' \"$code\" >> {report_dir / 'yamllint_repo.txt'}; exit 0"
            ),
        ),
        CommandSpec(
            artifact_name="shellcheck_repo.txt",
            lane="shell_style",
            tool="shellcheck",
            failure_class="shellcheck_error",
            subsystem="yaml_shell_json_misc",
            command=(
                "git ls-files '*.sh' | xargs -r shellcheck --format=gcc"
                f" > {report_dir / 'shellcheck_repo.txt'} 2>&1; "
                f"code=$?; printf '\\nEXIT_CODE=%s\\n' \"$code\" >> {report_dir / 'shellcheck_repo.txt'}; exit 0"
            ),
        ),
        CommandSpec(
            artifact_name="doc_dap_validate.txt",
            lane="docs_semantic",
            tool="doc_steward",
            failure_class="doc_semantic_error",
            subsystem="docs_semantic",
            command=(
                f"{PYTHON_EXE} -m doc_steward.cli dap-validate ."
                f" > {report_dir / 'doc_dap_validate.txt'} 2>&1; "
                f"code=$?; printf '\\nEXIT_CODE=%s\\n' \"$code\" >> {report_dir / 'doc_dap_validate.txt'}; exit 0"
            ),
        ),
        CommandSpec(
            artifact_name="doc_index_check.txt",
            lane="docs_semantic",
            tool="doc_steward",
            failure_class="doc_semantic_error",
            subsystem="docs_semantic",
            command=(
                f"{PYTHON_EXE} -m doc_steward.cli index-check . docs/INDEX.md"
                f" > {report_dir / 'doc_index_check.txt'} 2>&1; "
                f"code=$?; printf '\\nEXIT_CODE=%s\\n' \"$code\" >> {report_dir / 'doc_index_check.txt'}; exit 0"
            ),
            notes="two_argument_validator",
        ),
        CommandSpec(
            artifact_name="doc_link_check.txt",
            lane="docs_semantic",
            tool="doc_steward",
            failure_class="doc_semantic_error",
            subsystem="docs_semantic",
            command=(
                f"{PYTHON_EXE} -m doc_steward.cli link-check ."
                f" > {report_dir / 'doc_link_check.txt'} 2>&1; "
                f"code=$?; printf '\\nEXIT_CODE=%s\\n' \"$code\" >> {report_dir / 'doc_link_check.txt'}; exit 0"
            ),
        ),
        CommandSpec(
            artifact_name="doc_opencode_validate.txt",
            lane="docs_semantic",
            tool="doc_steward",
            failure_class="doc_semantic_error",
            subsystem="docs_semantic",
            command=(
                f"{PYTHON_EXE} -m doc_steward.cli opencode-validate ."
                f" > {report_dir / 'doc_opencode_validate.txt'} 2>&1; "
                f"code=$?; printf '\\nEXIT_CODE=%s\\n' \"$code\" >> {report_dir / 'doc_opencode_validate.txt'}; exit 0"
            ),
        ),
        CommandSpec(
            artifact_name="doc_admin_structure_check.txt",
            lane="docs_semantic",
            tool="doc_steward",
            failure_class="doc_semantic_error",
            subsystem="docs_semantic",
            command=(
                f"{PYTHON_EXE} -m doc_steward.cli admin-structure-check ."
                f" > {report_dir / 'doc_admin_structure_check.txt'} 2>&1; "
                f"code=$?; printf '\\nEXIT_CODE=%s\\n' \"$code\" >> {report_dir / 'doc_admin_structure_check.txt'}; exit 0"
            ),
        ),
        CommandSpec(
            artifact_name="doc_admin_archive_link_ban_check.txt",
            lane="docs_semantic",
            tool="doc_steward",
            failure_class="doc_semantic_error",
            subsystem="docs_semantic",
            command=(
                f"{PYTHON_EXE} -m doc_steward.cli admin-archive-link-ban-check ."
                f" > {report_dir / 'doc_admin_archive_link_ban_check.txt'} 2>&1; "
                f"code=$?; printf '\\nEXIT_CODE=%s\\n' \"$code\" >> {report_dir / 'doc_admin_archive_link_ban_check.txt'}; exit 0"
            ),
        ),
        CommandSpec(
            artifact_name="doc_freshness_check.txt",
            lane="docs_semantic",
            tool="doc_steward",
            failure_class="doc_semantic_error",
            subsystem="docs_semantic",
            command=(
                f"{PYTHON_EXE} -m doc_steward.cli freshness-check ."
                f" > {report_dir / 'doc_freshness_check.txt'} 2>&1; "
                f"code=$?; printf '\\nEXIT_CODE=%s\\n' \"$code\" >> {report_dir / 'doc_freshness_check.txt'}; exit 0"
            ),
        ),
        CommandSpec(
            artifact_name="doc_protocols_structure_check.txt",
            lane="docs_semantic",
            tool="doc_steward",
            failure_class="doc_semantic_error",
            subsystem="docs_semantic",
            command=(
                f"{PYTHON_EXE} -m doc_steward.cli protocols-structure-check ."
                f" > {report_dir / 'doc_protocols_structure_check.txt'} 2>&1; "
                f"code=$?; printf '\\nEXIT_CODE=%s\\n' \"$code\" >> {report_dir / 'doc_protocols_structure_check.txt'}; exit 0"
            ),
        ),
        CommandSpec(
            artifact_name="doc_runtime_structure_check.txt",
            lane="docs_semantic",
            tool="doc_steward",
            failure_class="doc_semantic_error",
            subsystem="docs_semantic",
            command=(
                f"{PYTHON_EXE} -m doc_steward.cli runtime-structure-check ."
                f" > {report_dir / 'doc_runtime_structure_check.txt'} 2>&1; "
                f"code=$?; printf '\\nEXIT_CODE=%s\\n' \"$code\" >> {report_dir / 'doc_runtime_structure_check.txt'}; exit 0"
            ),
        ),
        CommandSpec(
            artifact_name="doc_archive_structure_check.txt",
            lane="docs_semantic",
            tool="doc_steward",
            failure_class="doc_semantic_error",
            subsystem="docs_semantic",
            command=(
                f"{PYTHON_EXE} -m doc_steward.cli archive-structure-check ."
                f" > {report_dir / 'doc_archive_structure_check.txt'} 2>&1; "
                f"code=$?; printf '\\nEXIT_CODE=%s\\n' \"$code\" >> {report_dir / 'doc_archive_structure_check.txt'}; exit 0"
            ),
        ),
        CommandSpec(
            artifact_name="doc_docs_archive_link_ban_check.txt",
            lane="docs_semantic",
            tool="doc_steward",
            failure_class="doc_semantic_error",
            subsystem="docs_semantic",
            command=(
                f"{PYTHON_EXE} -m doc_steward.cli docs-archive-link-ban-check ."
                f" > {report_dir / 'doc_docs_archive_link_ban_check.txt'} 2>&1; "
                f"code=$?; printf '\\nEXIT_CODE=%s\\n' \"$code\" >> {report_dir / 'doc_docs_archive_link_ban_check.txt'}; exit 0"
            ),
        ),
        CommandSpec(
            artifact_name="doc_artefact_index_check.txt",
            lane="docs_semantic",
            tool="doc_steward",
            failure_class="doc_semantic_error",
            subsystem="docs_semantic",
            command=(
                f"{PYTHON_EXE} -m doc_steward.cli artefact-index-check ."
                f" > {report_dir / 'doc_artefact_index_check.txt'} 2>&1; "
                f"code=$?; printf '\\nEXIT_CODE=%s\\n' \"$code\" >> {report_dir / 'doc_artefact_index_check.txt'}; exit 0"
            ),
        ),
        CommandSpec(
            artifact_name="doc_version_duplicate_scan.txt",
            lane="docs_semantic",
            tool="doc_steward",
            failure_class="doc_semantic_error",
            subsystem="docs_semantic",
            command=(
                f"{PYTHON_EXE} -m doc_steward.cli version-duplicate-scan ."
                f" > {report_dir / 'doc_version_duplicate_scan.txt'} 2>&1; "
                f"code=$?; printf '\\nEXIT_CODE=%s\\n' \"$code\" >> {report_dir / 'doc_version_duplicate_scan.txt'}; exit 0"
            ),
        ),
        CommandSpec(
            artifact_name="hook_gate_tests.txt",
            lane="enforcement_chain",
            tool="pytest",
            failure_class="enforcement_error",
            subsystem="scripts_root_config",
            command=(
                "pytest -q runtime/tests/test_build_entry_gate.py runtime/tests/test_workflow_pack.py"
                f" > {report_dir / 'hook_gate_tests.txt'} 2>&1; "
                f"code=$?; printf '\\nEXIT_CODE=%s\\n' \"$code\" >> {report_dir / 'hook_gate_tests.txt'}; exit 0"
            ),
        ),
        CommandSpec(
            artifact_name="pytest_fast_fail.txt",
            lane="runtime_baseline",
            tool="pytest",
            failure_class="runtime_baseline_error",
            subsystem="runtime",
            command=(
                "pytest runtime/tests -q -x"
                f" > {report_dir / 'pytest_fast_fail.txt'} 2>&1; "
                f"code=$?; printf '\\nEXIT_CODE=%s\\n' \"$code\" >> {report_dir / 'pytest_fast_fail.txt'}; exit 0"
            ),
            notes="context_only",
        ),
    ]


def extract_exit_code(output: str) -> int | None:
    for line in reversed(output.splitlines()):
        if line.startswith("EXIT_CODE="):
            try:
                return int(line.split("=", 1)[1].strip())
            except ValueError:
                return None
    return None


def nonempty_lines(output: str) -> list[str]:
    lines = []
    for raw in output.splitlines():
        line = raw.strip()
        if not line or line.startswith("EXIT_CODE=") or line.startswith("TIMEOUT_SECONDS="):
            continue
        lines.append(line)
    return lines


def representative_examples(output: str, limit: int = 5) -> list[str]:
    return nonempty_lines(output)[:limit]


def finding_count(output: str, exit_code: int) -> int:
    if exit_code == 0:
        return 0
    return len(nonempty_lines(output))


def classify_disposition(tool: str, subsystem: str, exit_code: int, notes: str) -> str:
    if subsystem == "opencode_governance":
        return "exclude_or_rescope"
    if exit_code == 0:
        return "blocking_ready"
    if "waiver_candidate" in notes:
        return "needs_waiver"
    return "advisory_keep"


def expand_subsystems(raw_subsystem: str) -> list[str]:
    if raw_subsystem == "runtime+doc_steward+recursive_kernel+project_builder":
        return ["runtime", "doc_steward", "recursive_kernel", "project_builder"]
    return [raw_subsystem]


def build_finding_matrix(
    repo_root: Path,
    command_specs: Iterable[CommandSpec],
    command_outputs: dict[str, dict],
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for spec in command_specs:
        result = command_outputs[spec.artifact_name]
        exit_code = int(result["exit_code"])
        output = str(result["output"])
        for subsystem in expand_subsystems(spec.subsystem):
            rows.append(
                {
                    "lane": spec.lane,
                    "tool": spec.tool,
                    "failure_class": spec.failure_class,
                    "path_or_subsystem": subsystem,
                    "finding_count": finding_count(output, exit_code),
                    "representative_examples": representative_examples(output),
                    "exit_code": exit_code,
                    "disposition": classify_disposition(spec.tool, subsystem, exit_code, spec.notes),
                    "recommended_owner": owner_for_subsystem(subsystem),
                    "notes": spec.notes,
                    "artifact": str((REPORT_DIR_REL / spec.artifact_name)),
                }
            )
    matrix_path = repo_root / REPORT_DIR_REL / "finding_matrix.json"
    _write_text(matrix_path, json.dumps(rows, indent=2, sort_keys=True) + "\n")
    return rows


def owner_for_subsystem(subsystem: str) -> str:
    if subsystem == "runtime":
        return "runtime"
    if subsystem == "doc_steward":
        return "doc_steward"
    if subsystem == "recursive_kernel":
        return "recursive_kernel"
    if subsystem == "project_builder":
        return "project_builder"
    if subsystem == "docs_semantic":
        return "doc_steward"
    if subsystem == "docs_markdown_style":
        return "doc_steward"
    if subsystem == "opencode_governance":
        return "opencode"
    return "repo_hygiene"


def grouped_failures(rows: list[dict[str, object]]) -> dict[str, list[dict[str, object]]]:
    grouped: dict[str, list[dict[str, object]]] = {}
    for row in rows:
        if int(row["exit_code"]) == 0:
            continue
        grouped.setdefault(str(row["path_or_subsystem"]), []).append(row)
    return grouped


def known_pytest_failure(output: str) -> str | None:
    for line in output.splitlines():
        if line.startswith("FAILED "):
            return line.removeprefix("FAILED ").strip()
    return None


def runtime_baseline_status(output: str) -> str:
    for line in output.splitlines():
        if line.startswith("TIMEOUT_SECONDS="):
            seconds = line.split("=", 1)[1].strip()
            return f"timed out after {seconds} second(s) before first failure"
    if failure := known_pytest_failure(output):
        return failure
    exit_code = extract_exit_code(output)
    if exit_code == 0:
        return "passed within audit budget"
    if output.strip():
        return "incomplete artifact; see pytest_fast_fail.txt"
    return "no output captured"


def pre_commit_status(repo_root: Path) -> dict[str, str]:
    hook_src = repo_root / "scripts/hooks/pre-commit"
    hook_dst = repo_root / ".git/hooks/pre-commit"
    installed = hook_dst.exists() and os.access(hook_dst, os.X_OK)
    matches = installed and filecmp.cmp(hook_src, hook_dst, shallow=False)
    if installed and matches:
        status = "installed_and_matching"
    elif installed:
        status = "installed_but_drifted"
    else:
        status = "not_installed"

    lines = [
        f"source_hook={hook_src.relative_to(repo_root)}",
        f"installed_hook={hook_dst.relative_to(repo_root)}",
        f"installed={str(installed).lower()}",
        f"matches={str(matches).lower()}",
        f"status={status}",
    ]
    _write_text(repo_root / REPORT_DIR_REL / "pre_commit_installation.txt", "\n".join(lines) + "\n")
    return {"status": status, "installed": str(installed).lower(), "matches": str(matches).lower()}


def root_markdown_gap(repo_root: Path) -> list[str]:
    proc = subprocess.run(
        _shell("git ls-files '*.md' ':!:docs/**'"),
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
    )
    files = [line.strip() for line in proc.stdout.splitlines() if line.strip()]
    _write_text(repo_root / REPORT_DIR_REL / "root_markdown_out_of_scope.txt", "\n".join(files) + ("\n" if files else ""))
    return files


def write_environment(repo_root: Path) -> None:
    commands = [
        "python --version",
        "ruff --version",
        "mypy --version",
        "biome --version",
        "markdownlint --version",
        "yamllint --version",
        "shellcheck --version",
        "node --version",
        "npm --version",
    ]
    lines: list[str] = []
    for cmd in commands:
        proc = subprocess.run(_shell(cmd), cwd=repo_root, check=False, capture_output=True, text=True)
        output = (proc.stdout or "").strip() or (proc.stderr or "").strip()
        lines.append(f"$ {cmd}")
        lines.append(output or "<no output>")
        lines.append(f"EXIT_CODE={proc.returncode}")
        lines.append("")
    _write_text(repo_root / REPORT_DIR_REL / "environment.txt", "\n".join(lines).rstrip() + "\n")


def update_docs_index(repo_root: Path) -> None:
    path = repo_root / DOCS_INDEX_REL
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    updated: list[str] = []
    inserted = False
    row = "| [QUALITY_AUDIT_BASELINE_v1.0.md](./11_admin/QUALITY_AUDIT_BASELINE_v1.0.md) | **Audit baseline** — Repo-wide quality findings, evidence, and promotion recommendations |"
    for line in lines:
        if line.startswith("Last Updated: "):
            updated.append(f"Last Updated: {utc_date()}")
            continue
        updated.append(line)
        if "TECH_DEBT_INVENTORY.md" in line and row not in text:
            updated.append(row)
            inserted = True
    if not inserted and row not in text:
        updated.append("")
        updated.append(row)
    _write_text(path, "\n".join(updated) + "\n")


def update_tech_debt_inventory(repo_root: Path) -> None:
    path = repo_root / TECH_DEBT_REL
    text = path.read_text(encoding="utf-8")
    section_header = "## Audit References"
    entry = (
        f"- {utc_date()}: [QUALITY_AUDIT_BASELINE_v1.0.md](./QUALITY_AUDIT_BASELINE_v1.0.md) "
        "— repo-wide quality baseline audit. Cross-reference Item 4 (Logging Inconsistency) "
        "and Item 5 (Validation Pattern Fragmentation) when triaging follow-up cleanup."
    )
    if section_header in text:
        if entry in text:
            return
        text = text.replace(section_header, f"{section_header}\n\n{entry}", 1)
    else:
        marker = "---\n\n"
        insertion = f"---\n\n{section_header}\n\n{entry}\n\n"
        if marker in text:
            text = text.replace(marker, insertion, 1)
        else:
            text = f"{text.rstrip()}\n\n{section_header}\n\n{entry}\n"
    _write_text(path, text if text.endswith("\n") else text + "\n")


def render_summary(
    quality_payload: dict,
    doctor_payload: dict,
    rows: list[dict[str, object]],
    hook_status: dict[str, str],
    root_markdown_files: list[str],
    pytest_output: str,
) -> str:
    grouped = grouped_failures(rows)
    failing_groups = sorted(grouped.items(), key=lambda item: len(item[1]), reverse=True)
    runtime_status = runtime_baseline_status(pytest_output)
    manifest = load_quality_manifest(REPO_ROOT)
    advisory_tools = [
        name for name, cfg in manifest.get("tools", {}).items() if cfg.get("mode") == "advisory"
    ]
    failing_lines = []
    for subsystem, failures in failing_groups[:8]:
        tools = ", ".join(sorted({str(row["tool"]) for row in failures}))
        failing_lines.append(f"- `{subsystem}`: {len(failures)} failing lane(s) across {tools}")
    if not failing_lines:
        failing_lines.append("- No failing audit lanes were recorded.")

    blocking_ready = sorted({str(row["path_or_subsystem"]) for row in rows if str(row["disposition"]) == "blocking_ready"})
    advisory_keep = sorted({str(row["path_or_subsystem"]) for row in rows if str(row["disposition"]) == "advisory_keep"})
    rescope = sorted({str(row["path_or_subsystem"]) for row in rows if str(row["disposition"]) == "exclude_or_rescope"})

    return "\n".join(
        [
            "# Quality Audit Baseline v1.0",
            "",
            f"Generated: {utc_timestamp()}",
            "",
            "## Why This Exists",
            "",
            "LifeOS now has a real quality gate, but a gate only proves enforcement exists. "
            "This audit establishes where the repo already conforms, where debt is concentrated, "
            "and what can safely be promoted next without guessing.",
            "",
            "## Environment",
            "",
            "- Audit environment: Python venv + repo quality toolchain",
            f"- Quality doctor passed: `{str(doctor_payload.get('passed', False)).lower()}`",
            f"- Tool availability rows: `{len(doctor_payload.get('results', []))}`",
            "",
            "## Current Standard Conformance",
            "",
            f"- Repo-scope quality gate passed: `{str(quality_payload.get('passed', False)).lower()}`",
            f"- Summary: {quality_payload.get('summary', '')}",
            f"- Advisory tools in current policy: `{', '.join(advisory_tools)}`",
            "",
            "## Top Debt Clusters",
            "",
            *failing_lines,
            "",
            "## Enforcement Chain",
            "",
            f"- Pre-commit installation status: `{hook_status['status']}`",
            "- Hook logic evidence: `artifacts/reports/quality_audit_baseline_v1/hook_gate_tests.txt`",
            "",
            "## Scope Gaps and Differential Lanes",
            "",
            f"- Root Markdown outside current quality-gate scope: `{len(root_markdown_files)}` file(s)",
            "- `opencode_governance` is packaged in `pyproject.toml` but omitted from manifest python targets; audited separately as a manifest-scope gap.",
            "- `biome check .` is broader than the day-to-day quality router and is used here for baseline signal collection.",
            "",
            "## Runtime Baseline Context",
            "",
            f"- Runtime baseline status: `{runtime_status}`",
            "- Runtime failures are contextual baseline evidence only and are not merged into the quality findings matrix.",
            "",
            "## Promotion Guidance",
            "",
            f"- Blocking-ready buckets: `{', '.join(blocking_ready) if blocking_ready else 'none yet'}`",
            f"- Keep advisory for now: `{', '.join(advisory_keep) if advisory_keep else 'none'}`",
            f"- Exclude or rescope: `{', '.join(rescope) if rescope else 'none'}`",
            "- Recommended follow-up order: core Python ruff cleanup, biome/docs markdown, yamllint/shellcheck promotion decision, mypy by package, manifest decision for `opencode_governance`, then any root-Markdown scope expansion.",
            "",
            "## Evidence Bundle",
            "",
            "- Raw outputs: `artifacts/reports/quality_audit_baseline_v1/`",
            "- Findings matrix: `artifacts/reports/quality_audit_baseline_v1/finding_matrix.json`",
            "- Policy conformance: `artifacts/reports/quality_audit_baseline_v1/quality_gate_repo.json`",
            "",
        ]
    ) + "\n"


def run_audit(repo_root: Path) -> int:
    report_dir = repo_root / REPORT_DIR_REL
    report_dir.mkdir(parents=True, exist_ok=True)
    write_environment(repo_root)

    doctor_payload = capture_json_command(
        repo_root,
        f"{PYTHON_EXE} scripts/workflow/quality_gate.py doctor --json",
        report_dir / "doctor.json",
        timeout_seconds=60,
    )
    if not all(bool(row.get("present")) for row in doctor_payload.get("results", []) if row.get("enabled")):
        raise RuntimeError("quality doctor failed; install all required tools before running the audit")

    quality_payload = capture_json_command(
        repo_root,
        f"{PYTHON_EXE} scripts/workflow/quality_gate.py check --scope repo --json",
        report_dir / "quality_gate_repo.json",
        timeout_seconds=60,
    )

    specs = audit_command_specs(report_dir)
    outputs: dict[str, dict] = {}
    for spec in specs:
        outputs[spec.artifact_name] = capture_command(repo_root, spec.command, report_dir / spec.artifact_name)

    hook_status = pre_commit_status(repo_root)
    root_markdown_files = root_markdown_gap(repo_root)
    rows = build_finding_matrix(repo_root, specs, outputs)
    summary = render_summary(
        quality_payload,
        doctor_payload,
        rows,
        hook_status,
        root_markdown_files,
        outputs["pytest_fast_fail.txt"]["output"],
    )
    _write_text(repo_root / SUMMARY_REL, summary)
    update_docs_index(repo_root)
    update_tech_debt_inventory(repo_root)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=".", help="Repository root (default: current directory).")
    args = parser.parse_args()
    repo_root = Path(args.repo_root).resolve()
    return run_audit(repo_root)


if __name__ == "__main__":
    raise SystemExit(main())
