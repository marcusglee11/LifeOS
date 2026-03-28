---
artifact_type: review_packet
version: 1.0
terminal_outcome: PASS
closure_evidence:
  audit_reports: artifacts/reports/quality_audit_baseline_v1
  summary_doc: docs/11_admin/QUALITY_AUDIT_BASELINE_v1.0.md
---

# Scope Envelope

- Mission: implement the repo-wide quality audit baseline plan and close the build through the standard stewardship gates.
- Envelope: audit runner, audit evidence bundle, admin docs updates, admin allowlist update, and required doc-steward closeout artifacts.
- Exclusions: no quality-policy promotion changes, no manifest/mypy-baseline edits, no repo-wide cleanup beyond measurement artifacts.

# Summary

- Added `scripts/workflow/run_quality_audit_baseline.py` and `runtime/tests/test_quality_audit_baseline.py` for repeatable repo-wide baseline capture.
- Generated the baseline evidence bundle under `artifacts/reports/quality_audit_baseline_v1/` and wrote the human summary to `docs/11_admin/QUALITY_AUDIT_BASELINE_v1.0.md`.
- Updated `doc_steward/admin_structure_validator.py` and `docs/11_admin/DECISIONS.md` so the new audit summary is a first-class admin artifact rather than a structural violation.
- Regenerated strategic context after the doc changes using `python3 docs/scripts/generate_strategic_context.py`.

# Issue Catalogue

| ID | Finding | Disposition | Notes |
| --- | --- | --- | --- |
| IC-01 | Repo-scope `quality_gate.py check --scope repo` times out on this `/mnt/c` worktree after 60 seconds. | Recorded | Captured as policy-conformance evidence in `quality_gate_repo.json`; not treated as a clean pass. |
| IC-02 | Runtime fast-fail baseline does not reach a first failing test within the 300 second audit budget. | Recorded | Summary states timeout explicitly instead of implying a known failure was seen. |
| IC-03 | `docs/11_admin/QUALITY_AUDIT_BASELINE_v1.0.md` initially failed admin structure validation until the allowlist was updated. | Resolved | Decision log and validator now record the new admin artifact explicitly. |

# Acceptance Criteria

| ID | Criterion | Status | Evidence Pointer | SHA-256 |
| --- | --- | --- | --- | --- |
| AC-01 | Audit runner and tests were added for repo-wide baseline capture. | PASS | scripts/workflow/run_quality_audit_baseline.py | cf2064414cbf8dea29984cc70d02a89c64feeb26c7bb49757af2883b0eda89dd |
| AC-02 | Repo-wide audit evidence bundle was generated and committed under artifacts/reports. | PASS | artifacts/reports/quality_audit_baseline_v1/finding_matrix.json | e2323d2b42b3354e622e9aa4e41ebf9ffca78c845d68013f6fcc011269064e0d |
| AC-03 | Admin documentation was updated with the baseline summary and debt cross-reference. | PASS | docs/11_admin/QUALITY_AUDIT_BASELINE_v1.0.md | d0905f99607d1002fc9341d8224db7d8c90a819feb6ba244e299d2f4869d4ab5 |
| AC-04 | The admin allowlist and decision log were updated for the new audit summary. | PASS | doc_steward/admin_structure_validator.py | 6964eb3cee527bb35fe7dcb5253cbe0f7144341735e9fedcb58cae8126f493bf |
| AC-05 | Focused verification passed for the new audit-runner surface. | PASS | runtime/tests/test_quality_audit_baseline.py | 402ef4d9e7af6e4f51e46f3915ef8358e03c4f086a36da00fd6a4c0cbf218999 |

# Closure Evidence Checklist

| Item | Evidence | Verification |
| --- | --- | --- |
| Provenance | Worktree `build/repo-quality-audit-baseline` plus this packet. | Verified against current worktree files and artifacts. |
| Artifacts | `artifacts/reports/quality_audit_baseline_v1/` and `docs/11_admin/QUALITY_AUDIT_BASELINE_v1.0.md`. | Present and referenced in Acceptance Criteria. |
| Repro | `pytest -q runtime/tests/test_quality_audit_baseline.py`, `python3 -m doc_steward.cli admin-structure-check .`, and regenerated corpus command. | Commands rerun after the allowlist and markdown cleanup fixes. |
| Governance | No protected governance documents were modified. | Verified by changed-file set. |
| Outcome | Audit baseline implemented, documented, and admitted through the admin structure gate. | Ready for closure review. |

# Non-Goals

- This packet does not claim repo-wide conformance to the new standard.
- This packet does not promote any advisory tool to blocking mode.
- This packet does not remediate the repo-wide lint/type debt found by the audit.

# Appendix

## Appendix A: Flattened Source and Doc Content

### FILE: `scripts/workflow/run_quality_audit_baseline.py`

```py
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
```

### FILE: `runtime/tests/test_quality_audit_baseline.py`

```py
from __future__ import annotations

from scripts.workflow.run_quality_audit_baseline import (
    append_exit_footer,
    classify_disposition,
    expand_subsystems,
    extract_exit_code,
    finding_count,
    known_pytest_failure,
    nonempty_lines,
    representative_examples,
    runtime_baseline_status,
)


def test_extract_exit_code_reads_footer() -> None:
    output = "line one\nline two\nEXIT_CODE=17\n"
    assert extract_exit_code(output) == 17


def test_nonempty_lines_ignores_exit_footer_and_blanks() -> None:
    output = "\nwarning one\n\nEXIT_CODE=1\n"
    assert nonempty_lines(output) == ["warning one"]


def test_nonempty_lines_ignores_timeout_footer() -> None:
    output = "warning one\nTIMEOUT_SECONDS=300\nEXIT_CODE=124\n"
    assert nonempty_lines(output) == ["warning one"]


def test_finding_count_zero_when_command_passes() -> None:
    output = "all good\nEXIT_CODE=0\n"
    assert finding_count(output, 0) == 0


def test_finding_count_counts_nonempty_output_lines_on_failure() -> None:
    output = "issue one\nissue two\nEXIT_CODE=1\n"
    assert finding_count(output, 1) == 2


def test_representative_examples_limits_output() -> None:
    output = "a\nb\nc\nd\nEXIT_CODE=1\n"
    assert representative_examples(output, limit=2) == ["a", "b"]


def test_classify_disposition_marks_opencode_governance_for_rescope() -> None:
    assert classify_disposition("ruff_check", "opencode_governance", 1, "packaged_but_not_in_manifest") == "exclude_or_rescope"


def test_expand_subsystems_splits_governed_python_roots() -> None:
    assert expand_subsystems("runtime+doc_steward+recursive_kernel+project_builder") == [
        "runtime",
        "doc_steward",
        "recursive_kernel",
        "project_builder",
    ]


def test_classify_disposition_marks_success_as_blocking_ready() -> None:
    assert classify_disposition("ruff_check", "runtime", 0, "") == "blocking_ready"


def test_classify_disposition_defaults_failure_to_advisory_keep() -> None:
    assert classify_disposition("mypy", "runtime", 1, "") == "advisory_keep"


def test_known_pytest_failure_extracts_first_failed_nodeid() -> None:
    output = (
        "some setup\n"
        "FAILED runtime/tests/orchestration/coo/test_promotion_fixtures.py::test_all_promotion_fixtures\n"
        "more text\n"
    )
    assert (
        known_pytest_failure(output)
        == "runtime/tests/orchestration/coo/test_promotion_fixtures.py::test_all_promotion_fixtures"
    )


def test_append_exit_footer_adds_timeout_and_exit_code() -> None:
    output = append_exit_footer("partial output", exit_code=124, timeout_seconds=300)
    assert output.endswith("TIMEOUT_SECONDS=300\nEXIT_CODE=124\n")


def test_runtime_baseline_status_reports_timeout() -> None:
    output = "partial output\nTIMEOUT_SECONDS=300\nEXIT_CODE=124\n"
    assert runtime_baseline_status(output) == "timed out after 300 second(s) before first failure"


def test_runtime_baseline_status_reports_pass() -> None:
    assert runtime_baseline_status("ok\nEXIT_CODE=0\n") == "passed within audit budget"
```

### FILE: `doc_steward/admin_structure_validator.py`

```py
"""
Admin structure validator for docs/11_admin/.

Enforces:
- Root file allowlist (REQUIRED + CANONICAL_OPTIONAL)
- Allowed subdirectories only (build_summaries/, archive/)
- Naming patterns for build summaries and archive subdirs
- Archive subdir README.md requirement

Fail-closed: any unexpected file or directory is an error.
"""
from __future__ import annotations

import re
from pathlib import Path

# Canonical allowlist for docs/11_admin/ root (exact)
REQUIRED_FILES = {
    "LIFEOS_STATE.md",
    "BACKLOG.md",
    "INBOX.md",
    "DECISIONS.md",
}

CANONICAL_OPTIONAL_FILES = {
    "LifeOS_Build_Loop_Production_Plan_v2.1.md",
    "LifeOS_Master_Execution_Plan_v1.1.md",
    "Plan_Supersession_Register.md",
    "Doc_Freshness_Gate_Spec_v1.0.md",
    "AUTONOMY_STATUS.md",
    "WIP_LOG.md",
    "lifeos-master-operating-manual-v2.1.md",
    "README.md",
    # Burn-in closure reports (produced by build/batch*-burn-in branches)
    "Batch1_BurnIn_Report.md",
    "Batch2_BurnIn_Report.md",
    # Tech debt inventory (living doc produced by audit passes)
    "TECH_DEBT_INVENTORY.md",
    # Repo-wide quality baseline summary (produced by quality audit passes)
    "QUALITY_AUDIT_BASELINE_v1.0.md",
}

ALLOWED_ROOT_FILES = REQUIRED_FILES | CANONICAL_OPTIONAL_FILES

# Allowed subdirectories (exact)
ALLOWED_SUBDIRS = {"build_summaries", "archive"}

# Naming patterns
BUILD_SUMMARY_PATTERN = re.compile(r'^.*_Build_Summary_\d{4}-\d{2}-\d{2}\.md$')
ARCHIVE_SUBDIR_PATTERN = re.compile(r'^\d{4}-\d{2}-\d{2}_[a-z0-9_]+$')


def check_admin_structure(repo_root: str) -> list[str]:
    """
    Validate docs/11_admin/ structure against canonical allowlist.

    Args:
        repo_root: Path to repository root

    Returns:
        List of error strings for violations (empty if valid)
    """
    errors: list[str] = []
    admin_dir = Path(repo_root).resolve() / "docs" / "11_admin"

    if not admin_dir.exists():
        return ["docs/11_admin/ does not exist"]

    if not admin_dir.is_dir():
        return ["docs/11_admin/ is not a directory"]

    # Check for missing REQUIRED files
    for required_file in REQUIRED_FILES:
        file_path = admin_dir / required_file
        if not file_path.exists():
            errors.append(f"Missing required file: docs/11_admin/{required_file}")

    # Scan root directory
    for item in admin_dir.iterdir():
        rel_name = item.name

        if item.is_dir():
            # Check subdirectory allowlist
            if rel_name not in ALLOWED_SUBDIRS:
                errors.append(
                    f"Unexpected subdirectory: docs/11_admin/{rel_name}/ "
                    f"(allowed: {', '.join(sorted(ALLOWED_SUBDIRS))})"
                )

            # Validate archive subdirectory structure
            if rel_name == "archive":
                for archive_subdir in item.iterdir():
                    if archive_subdir.is_dir():
                        if not ARCHIVE_SUBDIR_PATTERN.match(archive_subdir.name):
                            errors.append(
                                "Invalid archive subdir name: "
                                f"docs/11_admin/archive/{archive_subdir.name}/ "
                                f"(must match: YYYY-MM-DD_<topic>)"
                            )

                        # Check for required README.md
                        readme_path = archive_subdir / "README.md"
                        if not readme_path.exists():
                            errors.append(
                                "Missing README.md in archive subdir: "
                                f"docs/11_admin/archive/{archive_subdir.name}/"
                            )

        elif item.is_file():
            # Check root file allowlist
            if rel_name not in ALLOWED_ROOT_FILES:
                errors.append(
                    f"Unexpected file at root: docs/11_admin/{rel_name} "
                    f"(not in allowlist)"
                )

    # Validate build_summaries/ naming pattern
    build_summaries_dir = admin_dir / "build_summaries"
    if build_summaries_dir.exists() and build_summaries_dir.is_dir():
        for summary_file in build_summaries_dir.iterdir():
            if summary_file.is_file() and summary_file.suffix == ".md":
                if not BUILD_SUMMARY_PATTERN.match(summary_file.name):
                    errors.append(
                        "Invalid build summary name: "
                        f"docs/11_admin/build_summaries/{summary_file.name} "
                        f"(must match: *_Build_Summary_YYYY-MM-DD.md)"
                    )

    return errors
```

### FILE: `docs/11_admin/DECISIONS.md`

```md
# DECISION LOG (append-only; low volume)

<!-- markdownlint-disable MD013 -->

- **2026-03-28 — Decision:** Add `QUALITY_AUDIT_BASELINE_v1.0.md` to the admin allowlist
  - **Why:** The repo-wide quality audit baseline is a recurring admin control artifact
    that records evidence, debt posture, and promotion guidance.
  - **Scope:** `docs/11_admin/`, `doc_steward/admin_structure_validator.py`,
    and `docs/INDEX.md`
  - **Evidence:** `0ed3a2da`, `d78a90e2`, quality audit baseline evidence bundle

- **2026-01-02 — Decision:** Activate Tier-2.5 Semi-Autonomous Development Layer
  - **Why:** All activation conditions (F3, F4, F7) satisfied; Tier-2 tests 100% pass
  - **Scope:** Enables semi-autonomous doc stewardship, recursive builder, agentic missions
  - **Evidence:** [Tier2_Completion_Tier2.5_Activation_Ruling_v1.0.md](../01_governance/Tier2_Completion_Tier2.5_Activation_Ruling_v1.0.md)

- **2026-01-02 — Decision:** Approve Stewardship Runner for agent-triggered runs
  - **Why:** Provides authoritative gating mechanism for stewardship ops with mandatory dry-run
  - **Scope:** Runtime stewardship, doc hygiene automation
  - **Evidence:** [Council_Review_Stewardship_Runner_v1.0.md](../01_governance/Council_Review_Stewardship_Runner_v1.0.md)

- **2026-01-03 — Decision:** Adopt thin control plane v1.1
  - **Why:** Reduces friction by externalising in-head state; prevents scaffolding spiral
  - **Scope:** Project admin via LIFEOS_STATE, BACKLOG, DECISIONS, INBOX
  - **Evidence:** `293f227`, `docs/11_admin/`

- **2026-01-03 — Decision:** Upgrade thin control plane to v1.2
  - **Why:** Refine evidence rules (anchoring), clarify hygiene triggers, adopt default sequencing rule
  - **Scope:** Admin hygiene protocols and evidence standards
  - **Evidence:** `3e545f7`, `docs/11_admin/`

- **2026-01-06 — Decision:** Activate Core TDD Design Principles v1.0
  - **Why:** Governance-first determinism for Core Track (runtime/mission, runtime/reactive); fail-closed enforcement scanner
  - **Scope:** TDD principles, allowlist governance, deterministic harness discipline
  - **Evidence:** [Council_Ruling_Core_TDD_Principles_v1.0.md](../01_governance/Council_Ruling_Core_TDD_Principles_v1.0.md)

- **2026-01-07 — Decision:** PASS (GO) for CT-2 Phase 2 — OpenCode Doc Steward Activation
  - **Why:** Full hardening of gate logic, diff envelope, and evidence hygiene verified (v2.4)
  - **Scope:** Enforced doc-steward gate (Phase 2), structural-op blocking, fail-closed CI diff
  - **Evidence:** [Council_Ruling_OpenCode_DocSteward_CT2_Phase2_v1.1.md](../01_governance/Council_Ruling_OpenCode_DocSteward_CT2_Phase2_v1.1.md)
- **2026-01-07 — Decision:** PASS (GO) for Phase Gate Lift — Repair Bundle v1.3
  - **Why:** Full audit-mechanical remediation verified (v1.3); portability and determinism hygiene confirmed.
  - **Scope:** Authorizes transition from Hardening phase to Tier-2.5 Phase 2 Maintenance & Tier-3 Kickoff.
  - **Evidence:** `Bundle_COO_Runtime_Repair_v1.3.zip` (SHA256: `81AC0AB67B122359C0F8D6048F78818FE991F96349B6B24863A952495008D505`)

- **2026-01-23 — Decision:** CSO Role Constitution v1.0 Finalized
  - **Why:** Resolved Phase 3 approval condition C1; establishes Chief Strategy Officer role boundaries and responsibilities
  - **Scope:** Strategic planning, architectural decisions, long-range roadmap authority
  - **Decider:** Council
  - **Evidence:** [CSO_Role_Constitution_v1.0.md](../01_governance/CSO_Role_Constitution_v1.0.md)

- **2026-01-26 — Decision:** Trusted Builder Mode v1.1 Ratified
  - **Why:** Establishes autonomous build authority boundaries and guardrails for Phase 4 autonomous construction
  - **Scope:** Autonomous build loop policy, protected path enforcement, governance boundaries
  - **Decider:** Council
  - **Evidence:** [Council_Ruling_Trusted_Builder_Mode_v1.1.md](../01_governance/Council_Ruling_Trusted_Builder_Mode_v1.1.md)

- **2026-02-03 — Decision:** Phase 4 (4A0-4D) Merged to Main
  - **Why:** Full autonomous build loop stack validated (1327 passing tests); CEO Queue, Loop Spine, Test Executor, Code Autonomy all canonical
  - **Scope:** Autonomous build infrastructure operational; spine execution, policy hash, ledger integration, test execution complete
  - **Decider:** CEO (via Council authority)
  - **Evidence:** Merge commit `9f4ee41`, Phase 4A0-4D implementation, `docs/11_admin/LIFEOS_STATE.md`

- **2026-02-08 — Decision:** EOL Policy v1.0 Canonical
  - **Why:** Root cause fixed (system core.autocrlf conflict with .gitattributes); LF line endings enforced, clean gate hardened
  - **Scope:** Line ending normalization (289 files), config-aware clean gate, acceptance closure validator, 37 new tests
  - **Decider:** COO (policy execution)
  - **Evidence:** [EOL_Policy_v1.0.md](../02_protocols/EOL_Policy_v1.0.md), commits fixing CRLF issues, clean gate implementation

- **2026-02-14 — Decision:** E2E Spine Proof Complete (W5-T01)
  - **Why:** First successful autonomous build loop execution validated; core spine infrastructure proven through full 6-phase chain
  - **Scope:** Finalized Emergency_Declaration_Protocol v1.0 via autonomous run `run_20260214_053357`; fixed 2 blockers (obsolete model names, timeout)
  - **Decider:** COO Runtime (autonomous execution)
  - **Evidence:** [E2E_Spine_Proof_Build_Summary_2026-02-14.md](./build_summaries/E2E_Spine_Proof_Build_Summary_2026-02-14.md), terminal artifact `TP_run_20260214_053357.yaml`, commit `195bd4d`

- **2026-02-20 — Decision:** OpenCode CLI Config Complete — Use Paid Models for Production Autonomy
  - **Why:** Infrastructure audit revealed 4 blocking bugs preventing any autonomous commits; all fixed. Free models cannot complete the loop (reviewer returns prose not YAML). Paid claude-sonnet-4-5 via OpenRouter completes the full 6-phase loop in ~61s with autonomous commit.
  - **Scope:** OpenCode build loop is now production-capable. Required model: `openrouter/anthropic/claude-sonnet-4-5` (or better). Free models reserved for design/build roles only, never reviewer.
  - **Key finding:** OpenCode loop (~61s, ~$0.08/task) vs Claude Code direct (~30s, ~$0.01/task). OpenCode value is governance + audit trail, not speed/cost.
  - **Decider:** COO Runtime (autonomous execution + Claude Code sprint)
  - **Evidence:** [OpenCode_CLI_Config_Build_Summary_2026-02-20.md](./build_summaries/OpenCode_CLI_Config_Build_Summary_2026-02-20.md), autonomous commit `f7daab46`, `artifacts/comparison_results.jsonl`

<!-- markdownlint-enable MD013 -->
```

### FILE: `docs/11_admin/QUALITY_AUDIT_BASELINE_v1.0.md`

```md
# Quality Audit Baseline v1.0

Generated: 2026-03-28T06:18:08.635509Z

## Why This Exists

LifeOS now has a real quality gate, but a gate only proves enforcement exists.
This audit establishes where the repo already conforms, where debt is
concentrated, and what can safely be promoted next without guessing.

## Environment

- Audit environment: Python venv + repo quality toolchain
- Quality doctor passed: `true`
- Tool availability rows: `7`

## Current Standard Conformance

- Repo-scope quality gate passed: `false`
- Summary: command timed out after 60 second(s)
- Advisory tools in current policy: `mypy, yamllint, shellcheck`

## Top Debt Clusters

- `docs_semantic`: 13 failing lane(s) across doc_steward
- `runtime`: 4 failing lane(s) across mypy, pytest, ruff_check, ruff_format
- `doc_steward`: 3 failing lane(s) across mypy, ruff_check, ruff_format
- `recursive_kernel`: 3 failing lane(s) across mypy, ruff_check, ruff_format
- `project_builder`: 3 failing lane(s) across mypy, ruff_check, ruff_format
- `opencode_governance`: 3 failing lane(s) across mypy, ruff_check, ruff_format
- `scripts_root_config`: 2 failing lane(s) across biome, pytest
- `yaml_shell_json_misc`: 2 failing lane(s) across shellcheck, yamllint

## Enforcement Chain

- Pre-commit installation status: `not_installed`
- Hook logic evidence: `artifacts/reports/quality_audit_baseline_v1/hook_gate_tests.txt`

## Scope Gaps and Differential Lanes

- Root Markdown outside current quality-gate scope: `954` file(s)
- `opencode_governance` is packaged in `pyproject.toml` but omitted from
  manifest python targets; audited separately as a manifest-scope gap.
- `biome check .` is broader than the day-to-day quality router and is used
  here for baseline signal collection.

## Runtime Baseline Context

- Runtime baseline status: `timed out after 300 second(s) before first failure`
- Runtime failures are contextual baseline evidence only and are not merged
  into the quality findings matrix.

## Promotion Guidance

- Blocking-ready buckets: `none yet`
- Keep advisory for now: `doc_steward, docs_markdown_style, docs_semantic,
  project_builder, recursive_kernel, runtime, scripts_root_config,
  yaml_shell_json_misc`
- Exclude or rescope: `opencode_governance`
- Recommended follow-up order: core Python ruff cleanup, biome/docs markdown,
  yamllint/shellcheck promotion decision, mypy by package, manifest decision
  for `opencode_governance`, then any root-Markdown scope expansion.

## Evidence Bundle

- Raw outputs: `artifacts/reports/quality_audit_baseline_v1/`
- Findings matrix: `artifacts/reports/quality_audit_baseline_v1/finding_matrix.json`
- Policy conformance: `artifacts/reports/quality_audit_baseline_v1/quality_gate_repo.json`
```

### FILE: `docs/INDEX.md`

```md
# LifeOS Strategic Corpus [P26-02-28 (rev12)]

<!-- markdownlint-disable MD013 MD040 MD060 -->

Last Updated: 2026-03-28

**Authority**: [LifeOS Constitution v2.0](./00_foundations/LifeOS_Constitution_v2.0.md)

---

## Authority Chain

```
LifeOS Constitution v2.0 (Supreme)
        │
        └── Governance Protocol v1.0
                │
                ├── COO Operating Contract v1.0
                ├── DAP v2.0
                └── COO Runtime Spec v1.0
```

---

## Strategic Context

| Document | Purpose |
|----------|---------|
| [LifeOS_Strategic_Corpus.md](./LifeOS_Strategic_Corpus.md) | **Primary Context for the LifeOS Project** |

---

## Agent Guidance (Root Level)

| File | Purpose |
|------|---------|
| [CLAUDE.md](../CLAUDE.md) | Claude Code (claude.ai/code) agent guidance |
| [AGENTS.md](../AGENTS.md) | OpenCode agent instructions (Doc Steward subset) |
| [GEMINI.md](../GEMINI.md) | Gemini agent constitution |

---

## 00_admin — Project Admin (Thin Control Plane)

### Canonical Files

| Document | Purpose |
|----------|---------|
| [LIFEOS_STATE.md](./11_admin/LIFEOS_STATE.md) | **Single source of truth** — Current focus, WIP, blockers, next actions (auto-updated) |
| [BACKLOG.md](./11_admin/BACKLOG.md) | **Canonical backlog** — Actionable backlog (Now/Next/Later), target ≤40 items (auto-updated) |
| [DECISIONS.md](./11_admin/DECISIONS.md) | **Append-only** — Decision log (low volume) |
| [INBOX.md](./11_admin/INBOX.md) | Raw capture scratchpad for triage |
| [Plan_Supersession_Register.md](./11_admin/Plan_Supersession_Register.md) | **Control** — Canonical register of superseded and active plans |
| [LifeOS_Build_Loop_Production_Plan_v2.1.md](./11_admin/LifeOS_Build_Loop_Production_Plan_v2.1.md) | **Canonical plan** — Production readiness plan (per supersession register) |
| [LifeOS_Master_Execution_Plan_v1.1.md](./11_admin/LifeOS_Master_Execution_Plan_v1.1.md) | (superseded by v2.1) — Historical master execution plan W0–W7 |
| [Doc_Freshness_Gate_Spec_v1.0.md](./11_admin/Doc_Freshness_Gate_Spec_v1.0.md) | **Control** — Runtime-backed doc freshness and contradiction gate spec |
| [AUTONOMY_STATUS.md](./11_admin/AUTONOMY_STATUS.md) | **Derived view** — Autonomy capability matrix (derived from canonical sources) |
| [WIP_LOG.md](./11_admin/WIP_LOG.md) | **WIP tracker** — Work-in-progress log with controlled status enum |
| [lifeos-master-operating-manual-v2.1.md](./11_admin/lifeos-master-operating-manual-v2.1.md) | **Strategic context** — Master Operating Manual v2.1 |
| [TECH_DEBT_INVENTORY.md](./11_admin/TECH_DEBT_INVENTORY.md) | **Tech debt tracker** — Structural debt items with explicit trigger conditions |
| [QUALITY_AUDIT_BASELINE_v1.0.md](./11_admin/QUALITY_AUDIT_BASELINE_v1.0.md) | **Audit baseline** — Repo-wide quality findings, evidence, and promotion recommendations |
| [build_summaries/COO_Step6_LiveWiring_Build_Summary_2026-03-08.md](./11_admin/build_summaries/COO_Step6_LiveWiring_Build_Summary_2026-03-08.md) | COO Step 6 build summary — live wiring, shadow validation, gaps, workflow |

### Subdirectories

| Directory | Purpose | Naming Rule |
|-----------|---------|-------------|
| `build_summaries/` | Timestamped build evidence summaries | `*_Build_Summary_YYYY-MM-DD.md` |
| `archive/` | Historical documents (reference only; immutable) | Archive subdirs: `YYYY-MM-DD_<topic>/` |

---

## 00_foundations — Core Principles

| Document | Purpose |
|----------|---------|
| [LifeOS_Constitution_v2.0.md](./00_foundations/LifeOS_Constitution_v2.0.md) | **Supreme governing document** — Raison d'être, invariants, principles |
| [Anti_Failure_Operational_Packet_v0.1.md](./00_foundations/Anti_Failure_Operational_Packet_v0.1.md) | Anti-failure mechanisms, human preservation, workflow constraints |
| [Architecture_Skeleton_v1.0.md](./00_foundations/Architecture_Skeleton_v1.0.md) | High-level conceptual architecture (CEO/COO/Worker layers) |
| [Tier_Definition_Spec_v1.1.md](./00_foundations/Tier_Definition_Spec_v1.1.md) | **Canonical** — Tier progression model, definitions, and capabilities |
| [ARCH_Future_Build_Automation_Operating_Model_v0.2.md](./00_foundations/ARCH_Future_Build_Automation_Operating_Model_v0.2.md) | **Architecture Proposal** — Future Build Automation Operating Model v0.2 |
| [lifeos-agent-architecture.md](./00_foundations/lifeos-agent-architecture.md) | **Architecture** — Non-canonical agent architecture |
| [lifeos-maximum-vision.md](./00_foundations/lifeos-maximum-vision.md) | **Vision** — Non-canonical maximum vision architecture |

---

## 01_governance — Governance & Contracts

### Core Governance

| Document | Purpose |
|----------|---------|
| [COO_Operating_Contract_v1.0.md](./01_governance/COO_Operating_Contract_v1.0.md) | CEO/COO role boundaries and interaction rules |
| [AgentConstitution_GEMINI_Template_v1.0.md](./01_governance/AgentConstitution_GEMINI_Template_v1.0.md) | Template for agent GEMINI.md files |
| [DOC_STEWARD_Constitution_v1.0.md](./01_governance/DOC_STEWARD_Constitution_v1.0.md) | Document Steward constitutional boundaries |

### Council & Review

| Document | Purpose |
|----------|---------|
| [Council_Invocation_Runtime_Binding_Spec_v1.1.md](./01_governance/Council_Invocation_Runtime_Binding_Spec_v1.1.md) | Council invocation and runtime binding |
| [Antigravity_Council_Review_Packet_Spec_v1.0.md](./01_governance/Antigravity_Council_Review_Packet_Spec_v1.0.md) | Council review packet format |
| [ALIGNMENT_REVIEW_TEMPLATE_v1.0.md](./01_governance/ALIGNMENT_REVIEW_TEMPLATE_v1.0.md) | Monthly/quarterly alignment review template |

### Policies & Logs

| Document | Purpose |
|----------|---------|
| [COO_Expectations_Log_v1.0.md](./01_governance/COO_Expectations_Log_v1.0.md) | Working preferences and behavioral refinements |
| [Antigrav_Output_Hygiene_Policy_v0.1.md](./01_governance/Antigrav_Output_Hygiene_Policy_v0.1.md) | Output path rules for Antigravity |
| [OpenCode_First_Stewardship_Policy_v1.1.md](./01_governance/OpenCode_First_Stewardship_Policy_v1.1.md) | **Mandatory** OpenCode routing for in-envelope docs |

### Active Rulings

| Document | Purpose |
|----------|---------|
| [Council_Ruling_OpenCode_DocSteward_CT2_Phase2_v1.1.md](./01_governance/Council_Ruling_OpenCode_DocSteward_CT2_Phase2_v1.1.md) | **ACTIVE** — OpenCode Document Steward CT-2 Phase 2 Activation |
| [Council_Ruling_OpenCode_First_Stewardship_v1.1.md](./01_governance/Council_Ruling_OpenCode_First_Stewardship_v1.1.md) | **ACTIVE** — OpenCode-First Doc Stewardship Adoption |
| [Council_Ruling_Build_Handoff_v1.0.md](./01_governance/Council_Ruling_Build_Handoff_v1.0.md) | **Approved**: Build Handoff Protocol v1.0 activation-canonical |
| [Council_Ruling_Build_Loop_Architecture_v1.0.md](./01_governance/Council_Ruling_Build_Loop_Architecture_v1.0.md) | **ACTIVE**: Build Loop Architecture v0.3 authorised for Phase 1 |
| [Tier3_Reactive_Task_Layer_Council_Ruling_v0.1.md](./01_governance/Tier3_Reactive_Task_Layer_Council_Ruling_v0.1.md) | **Active**: Reactive Task Layer v0.1 Signoff |
| [Council_Review_Stewardship_Runner_v1.0.md](./01_governance/Council_Review_Stewardship_Runner_v1.0.md) | **Approved**: Stewardship Runner cleared for agent-triggered runs |

### Historical Rulings

| Document | Purpose |
|----------|---------|
| [Tier1_Hardening_Council_Ruling_v0.1.md](./01_governance/Tier1_Hardening_Council_Ruling_v0.1.md) | Historical: Tier-1 ratification ruling |
| [Tier1_Tier2_Activation_Ruling_v0.2.md](./01_governance/Tier1_Tier2_Activation_Ruling_v0.2.md) | Historical: Tier-2 activation ruling |
| [Tier1_Tier2_Conditions_Manifest_FP4x_v0.1.md](./01_governance/Tier1_Tier2_Conditions_Manifest_FP4x_v0.1.md) | Historical: Tier transition conditions |
| [Tier2_Completion_Tier2.5_Activation_Ruling_v1.0.md](./01_governance/Tier2_Completion_Tier2.5_Activation_Ruling_v1.0.md) | Historical: Tier-2.5 activation ruling |

---

## 02_protocols — Protocols & Agent Communication

### Batch 1 Runtime Protocols

> **Note:** The 5 Batch 1 runtime modules (`run_lock`, `invocation_receipt`, `invocation_schema`, `shadow_runner`, `shadow_capture`) do not yet have dedicated protocol docs in `02_protocols/`. Their protocol definitions are captured in:

| Document | Coverage |
|----------|---------|
| [LifeOS_Autonomous_Build_Loop_Architecture_v0.3.md](./03_runtime/LifeOS_Autonomous_Build_Loop_Architecture_v0.3.md) | **Batch 1**: run_lock, invocation_receipt, invocation_schema, shadow_runner, shadow_capture — autonomous build loop protocol definitions |

### Core Protocols

| Document | Purpose |
|----------|---------|
| [Governance_Protocol_v1.0.md](./02_protocols/Governance_Protocol_v1.0.md) | Envelopes, escalation rules, council model |
| [Git_Workflow_Protocol_v1.1.md](./02_protocols/Git_Workflow_Protocol_v1.1.md) | **Fail-Closed**: Branch conventions, CI proof merging, receipts |
| [Document_Steward_Protocol_v1.0.md](./02_protocols/Document_Steward_Protocol_v1.0.md) | Document creation, indexing, GitHub/Drive sync |
| [Deterministic_Artefact_Protocol_v2.0.md](./02_protocols/Deterministic_Artefact_Protocol_v2.0.md) | DAP — artefact creation, versioning, and storage rules |
| [Build_Artifact_Protocol_v1.0.md](./02_protocols/Build_Artifact_Protocol_v1.0.md) | **NEW** — Formal schemas/templates for Plans, Review Packets, Walkthroughs, etc. |
| [Tier-2_API_Evolution_and_Versioning_Strategy_v1.0.md](./02_protocols/Tier-2_API_Evolution_and_Versioning_Strategy_v1.0.md) | Tier-2 API Versioning, Deprecation, and Compatibility Rules |
| [Build_Handoff_Protocol_v1.0.md](./02_protocols/Build_Handoff_Protocol_v1.0.md) | Messaging & handoff architecture for agent coordination |
| [Intent_Routing_Rule_v1.1.md](./02_protocols/Intent_Routing_Rule_v1.1.md) | Decision routing (CEO/CSO/Council/Runtime) |
| [LifeOS_Design_Principles_Protocol_v1.1.md](./02_protocols/LifeOS_Design_Principles_Protocol_v1.1.md) | **Canonical** — "Prove then Harden" development principles, Output-First governance, sandbox workflow |
| [Emergency_Declaration_Protocol_v1.0.md](./02_protocols/Emergency_Declaration_Protocol_v1.0.md) | **Canonical** — Emergency override and auto-revert procedures |
| [Test_Protocol_v2.0.md](./02_protocols/Test_Protocol_v2.0.md) | **WIP** — Test categories, coverage, and flake policy |
| [EOL_Policy_v1.0.md](./02_protocols/EOL_Policy_v1.0.md) | **Canonical** — LF line endings, config compliance, clean invariant enforcement |
| [Filesystem_Error_Boundary_Protocol_v1.0.md](./02_protocols/Filesystem_Error_Boundary_Protocol_v1.0.md) | **Draft** — Fail-closed filesystem error boundaries, exception taxonomy |
| [GitHub_Actions_Secrets_Setup.md](./02_protocols/GitHub_Actions_Secrets_Setup.md) | PAT creation, secrets config, and rotation for CI workflows |

### Council Protocols

| Document | Purpose |
|----------|---------|
| [Council_Protocol_v1.3.md](./02_protocols/Council_Protocol_v1.3.md) | **Canonical** — Council review procedure, modes, topologies, P0 criteria, complexity budget |
| [AI_Council_Procedural_Spec_v1.1.md](./02_protocols/AI_Council_Procedural_Spec_v1.1.md) | Runbook for executing Council Protocol v1.2 |
| [Council_Context_Pack_Schema_v0.3.md](./02_protocols/Council_Context_Pack_Schema_v0.3.md) | CCP template schema for council reviews |

### Packet & Artifact Schemas

| Document | Purpose |
|----------|---------|
| [lifeos_packet_schemas_v1.yaml](./02_protocols/lifeos_packet_schemas_v1.yaml) | Agent packet schema definitions (13 packet types) |
| [lifeos_packet_templates_v1.yaml](./02_protocols/lifeos_packet_templates_v1.yaml) | Ready-to-use packet templates |
| [build_artifact_schemas_v1.yaml](./02_protocols/build_artifact_schemas_v1.yaml) | **NEW** — Build artifact schema definitions (6 artifact types) |
| [templates/](./02_protocols/templates/) | **NEW** — Markdown templates for all artifact types |
| [example_converted_antigravity_packet.yaml](./02_protocols/example_converted_antigravity_packet.yaml) | Example: converted Antigravity review packet |

---

## 03_runtime — Runtime Specification

### Core Specs

| Document | Purpose |
|----------|---------|
| [COO_Runtime_Spec_v1.0.md](./03_runtime/COO_Runtime_Spec_v1.0.md) | Mechanical execution contract, FSM, determinism rules |
| [COO_Runtime_Implementation_Packet_v1.0.md](./03_runtime/COO_Runtime_Implementation_Packet_v1.0.md) | Implementation details for Antigravity |
| [COO_Runtime_Core_Spec_v1.0.md](./03_runtime/COO_Runtime_Core_Spec_v1.0.md) | Extended core specification |
| [COO_Runtime_Spec_Index_v1.0.md](./03_runtime/COO_Runtime_Spec_Index_v1.0.md) | Spec index and patch log |
| [LifeOS_Autonomous_Build_Loop_Architecture_v0.3.md](./03_runtime/LifeOS_Autonomous_Build_Loop_Architecture_v0.3.md) | **Canonical**: Autonomous Build Loop Architecture (Council-authorised) |
| [Council_Agent_Design_v1.0.md](./03_runtime/Council_Agent_Design_v1.0.md) | **Information Only** — Conceptual design for the Council Agent |

### Roadmaps & Plans

| Document | Purpose |
|----------|---------|
| [LifeOS_Programme_Roadmap_CoreFuelPlumbing_v1.0.md](./03_runtime/LifeOS_Programme_Roadmap_CoreFuelPlumbing_v1.0.md) | **Current roadmap** — Core/Fuel/Plumbing tracks |
| [LifeOS_Recursive_Improvement_Architecture_v0.2.md](./03_runtime/LifeOS_Recursive_Improvement_Architecture_v0.2.md) | Recursive improvement architecture |
| [LifeOS_Router_and_Executor_Adapter_Spec_v0.1.md](./03_runtime/LifeOS_Router_and_Executor_Adapter_Spec_v0.1.md) | Future router and executor adapter spec |
| [LifeOS_Plan_SelfBuilding_Loop_v2.2.md](./03_runtime/LifeOS_Plan_SelfBuilding_Loop_v2.2.md) | **Plan**: Self-Building LifeOS — CEO Out of the Execution Loop (Milestone) |

### Work Plans & Fix Packs

| Document | Purpose |
|----------|---------|
| [Hardening_Backlog_v0.1.md](./03_runtime/Hardening_Backlog_v0.1.md) | Hardening work backlog |
| [Tier1_Hardening_Work_Plan_v0.1.md](./03_runtime/Tier1_Hardening_Work_Plan_v0.1.md) | Tier-1 hardening work plan |
| [Tier2.5_Unified_Fix_Plan_v1.0.md](./03_runtime/Tier2.5_Unified_Fix_Plan_v1.0.md) | Tier-2.5 unified fix plan |
| [F3_Tier2.5_Activation_Conditions_Checklist_v1.0.md](./03_runtime/F3_Tier2.5_Activation_Conditions_Checklist_v1.0.md) | Tier-2.5 activation conditions checklist (F3) |
| [F4_Tier2.5_Deactivation_Rollback_Conditions_v1.0.md](./03_runtime/F4_Tier2.5_Deactivation_Rollback_Conditions_v1.0.md) | Tier-2.5 deactivation and rollback conditions (F4) |
| [F7_Runtime_Antigrav_Mission_Protocol_v1.0.md](./03_runtime/F7_Runtime_Antigrav_Mission_Protocol_v1.0.md) | Runtime↔Antigrav mission protocol (F7) |
| [Runtime_Hardening_Fix_Pack_v0.1.md](./03_runtime/Runtime_Hardening_Fix_Pack_v0.1.md) | Runtime hardening fix pack |
| [fixpacks/FP-4x_Implementation_Packet_v0.1.md](./03_runtime/fixpacks/FP-4x_Implementation_Packet_v0.1.md) | FP-4x implementation |

### Templates & Tools

| Document | Purpose |
|----------|---------|
| [BUILD_STARTER_PROMPT_TEMPLATE_v1.0.md](./03_runtime/BUILD_STARTER_PROMPT_TEMPLATE_v1.0.md) | Build starter prompt template |
| [CODE_REVIEW_PROMPT_TEMPLATE_v1.0.md](./03_runtime/CODE_REVIEW_PROMPT_TEMPLATE_v1.0.md) | Code review prompt template |
| [COO_Runtime_Walkthrough_v1.0.md](./03_runtime/COO_Runtime_Walkthrough_v1.0.md) | Runtime walkthrough |
| [COO_Runtime_Clean_Build_Spec_v1.1.md](./03_runtime/COO_Runtime_Clean_Build_Spec_v1.1.md) | Clean build specification |

### Other

| Document | Purpose |
|----------|---------|
| [Automation_Proposal_v0.1.md](./03_runtime/Automation_Proposal_v0.1.md) | Automation proposal |
| [Runtime_Complexity_Constraints_v0.1.md](./03_runtime/Runtime_Complexity_Constraints_v0.1.md) | Complexity constraints |
| [README_Recursive_Kernel_v0.1.md](./03_runtime/README_Recursive_Kernel_v0.1.md) | Recursive kernel readme |

---

## 12_productisation — Productisation & Marketing

| Document | Purpose |
|----------|---------|
| [An_OS_for_Life.mp4](./12_productisation/assets/An_OS_for_Life.mp4) | **Promotional Video** — An introduction to LifeOS |

---

## internal — Internal Reports

| Document | Purpose |
|----------|---------|
| [OpenCode_Phase0_Completion_Report_v1.0.md](./internal/OpenCode_Phase0_Completion_Report_v1.0.md) | OpenCode Phase 0 API connectivity validation — PASSED |

---

## 99_archive — Historical Documents

Archived documents are in `99_archive/`. Key locations:

- `99_archive/superseded_by_constitution_v2/` — Documents superseded by Constitution v2.0
- `99_archive/legacy_structures/` — Legacy governance and specs
- `99_archive/lifeos-master-operating-manual-v2.md` — Preceding version of the master operations manual
- `99_archive/lifeos-operations-manual.md` — First version of the master operations manual

---

## Other Directories

| Directory | Contents |
|-----------|----------|
| `04_project_builder/` | Project builder specs |
| `05_agents/` | Agent architecture |
| `06_user_surface/` | User surface specs |
| `08_manuals/` | Operational manuals (COO Doc Management, Governance Runtime) |
| `09_prompts/v1.0/` | Legacy v1.0 prompt templates |
| `09_prompts/v1.2/` | **Current** — Council role prompts (Chair, Co-Chair, 10 reviewer seats) |
| `10_meta/` | Meta documents, reviews, tasks |

---

## 08_manuals — Operational Manuals

| Document | Purpose |
|----------|---------|
| [COO_Doc_Management_Manual_v1.0.md](./08_manuals/COO_Doc_Management_Manual_v1.0.md) | **Executable runbook** — Doc stewardship operations, validators, governance boundaries |
| [Governance_Runtime_Manual_v1.0.md](./08_manuals/Governance_Runtime_Manual_v1.0.md) | Governance runtime operations |

<!-- markdownlint-enable MD013 MD040 MD060 -->
```

### FILE: `docs/11_admin/TECH_DEBT_INVENTORY.md`

```md
# Tech Debt Inventory

<!-- markdownlint-disable MD013 MD032 MD060 -->

**Created:** 2026-02-27
**Source:** 3-Pass Audit (build/audit-3pass)
**Status:** Living document — update trigger conditions as items are resolved.

This inventory documents known structural debt with explicit **trigger conditions** for when each item becomes urgent. The goal is to track without over-engineering — fix things when they become obstacles, not before.

---

## Audit References

- 2026-03-28: [QUALITY_AUDIT_BASELINE_v1.0.md](./QUALITY_AUDIT_BASELINE_v1.0.md) — repo-wide quality baseline audit. Cross-reference Item 4 (Logging Inconsistency) and Item 5 (Validation Pattern Fragmentation) when triaging follow-up cleanup.

## 1. Orchestration Module Sprawl

**Location:** `runtime/orchestration/` (65+ files)
**Issue:** Single flat package containing functionally distinct subsystems: council (11 files), dispatch, loop, missions, receipts, transforms.
**Risk:** Naming collisions, slow imports, hard to onboard new contributors.

**Trigger:** _"If adding a new orchestration subsystem, extract `council/` or `dispatch/` to a peer module (`runtime/council/`, `runtime/dispatch/`) first."_

---

## 2. God Functions

**Issue:** Several functions exceed 100 lines. Functions this long are harder to test and modify safely.

| File | Function | Approx Lines |
|------|----------|-------------|
| `runtime/cli.py` | `main()` | ~167 |
| `runtime/cli.py` | `cmd_mission_run()` | ~140 |
| `runtime/orchestration/engine.py` | `run_workflow()` | ~130 |
| `runtime/orchestration/engine.py` | `_execute_mission()` | ~129 |
| `runtime/orchestration/council/fsm.py` | 2 methods | >100 each |

**Trigger:** _"If a function exceeds 200 lines OR gains new conditional branches, split it before adding more code."_

---

## 3. spine.py Complexity

**Location:** `runtime/orchestration/loop/spine.py` (~1,390 lines)
**Issue:** Single file handling the full autonomous build loop spine. Growing toward maintenance risk threshold.

**Trigger:** _"If `spine.py` exceeds 1,500 lines, split into `spine_core.py` + `spine_phases.py` before adding new phases."_

---

## 4. Logging Inconsistency

**Issue:** Mixed use of `print()` (~268 occurrences) and `logging` calls (~108 occurrences) across the codebase.
**Note:** CLI `print()` calls may be intentional (user-facing output). The inconsistency is in internal modules.

**Trigger:** _"If adding observability, monitoring, or structured log ingestion, unify all internal `print()` to `logger.*()` first."_

---

## 5. Validation Pattern Fragmentation

**Issue:** ~125 `validate_*` functions scattered across the codebase with no central registry. Similar validation logic is sometimes duplicated.

**Trigger:** _"If adding a new validation type that would be the 3rd+ similar validator in a module, consider a registry pattern first."_

---

## 6. Workspace Root Detection — Partial Consolidation

**Canonical:** `runtime/util/workspace.py:resolve_workspace_root()` (exported via `runtime.util`)
**Duplicates:**
- `runtime/governance/tool_policy.py:resolve_workspace_root()` — module-internal; raises `GovernanceUnavailable` (not `RuntimeError`). Safe consolidation requires exception wrapping — deferred.
- `runtime/config/repo_root.py:detect_repo_root()` — different semantics (walks `.git` markers, used by CLI). Not a duplicate; separate utility.

**Completed:** `runtime/governance/policy_loader.py` already delegates to `runtime.util.workspace`.

**Trigger:** _"If modifying `tool_policy.py:resolve_workspace_root()`, migrate it to delegate to `runtime.util.workspace` with `GovernanceUnavailable` wrapping at that time."_

---

## 7. Dual Steward Configs

**Location:** `config/Antigrav_DocSteward_Config_v0.1.yaml` + `config/steward_runner.yaml`
**Issue:** Two steward config files with potentially overlapping settings.

**Trigger:** _"Consolidate during the next steward feature work cycle."_

---

## 8. Closure Manifest Schema v1 vs v1.1

**Issue:** Schema v1 may be deprecated in favor of v1.1. Unclear if any code paths still reference v1.

**Action:** _"Verify no code references v1 exclusively, then remove v1 schema artifacts."_

---

## Resolved Items (from this audit)

The following items were **fixed** during the 2026-02-27 audit rather than documented:

| Item | Fix |
|------|-----|
| API key prefix in trace logs (`opencode_client.py:626`) | Replaced `or_key[:10]` with `***masked***` |
| Temp auth.json cleanup on abnormal exit | Added `atexit.register(self._cleanup_config)` in `_create_isolated_config()` |
| Full HTTP response body in debug logs | Truncated to 200 chars in 3 REST failure paths |
| `EnvelopeViolation` defined in 4 places | Consolidated to `runtime/errors.py`; 3 duplicates removed |
| Duplicate imports in `mission/__init__.py` | Removed duplicate `MissionSynthesisRequest` + `synthesize_mission` entries |

<!-- markdownlint-enable MD013 MD032 MD060 -->
```

## Appendix B: Audit Evidence Inventory

| Artifact | SHA-256 |
| --- | --- |
| `artifacts/reports/quality_audit_baseline_v1/doctor.json` | `27a61b9b8f7970b8322d055bec46ecfa17160dd9c3810b06b9a00ee8099fb783` |
| `artifacts/reports/quality_audit_baseline_v1/quality_gate_repo.json` | `438fa67a5848cd9a883bcba2f27248538c5f1c2f1099aac69103502250587c06` |
| `artifacts/reports/quality_audit_baseline_v1/finding_matrix.json` | `e2323d2b42b3354e622e9aa4e41ebf9ffca78c845d68013f6fcc011269064e0d` |
| `artifacts/reports/quality_audit_baseline_v1/environment.txt` | `27d095ced1ef6d9af7704755c5ee1065d8805bab570f30e42a66d08b952040ef` |
| `artifacts/reports/quality_audit_baseline_v1/pytest_fast_fail.txt` | `934c760ce1cb7a533401d87917c45be25812ec882e314b3cc04beb9cdda47988` |
| `artifacts/reports/quality_audit_baseline_v1/pre_commit_installation.txt` | `db2f6c4ad1ccf187b542196818253a71cad8cfb0dd3d9c4eb7b4e456ecc25185` |
| `artifacts/reports/quality_audit_baseline_v1/root_markdown_out_of_scope.txt` | `9fdf4b44f57b70478fee1a2a46f6e2864ad120d13c34bf399c9e38cc4328c4ad` |
| `artifacts/reports/quality_audit_baseline_v1/hook_gate_tests.txt` | `e43d9206f3220c9df6c384064c7c6d289a60703ed2d568f1fd668bb5ad794ccd` |

The full raw evidence bundle remains in `artifacts/reports/quality_audit_baseline_v1/`. Appendix B inventories the primary audit artifacts; Appendix A contains the authored source/doc changes in full.
