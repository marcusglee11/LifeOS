---
artifact_type: review_packet
version: 1.0
terminal_outcome: PASS
closure_evidence:
  summary_doc: docs/11_admin/QUALITY_AUDIT_BASELINE_v1.0.md
  finding_matrix: artifacts/reports/quality_audit_baseline_v1/finding_matrix.json
  environment_report: artifacts/reports/quality_audit_baseline_v1/environment.txt
---

# Scope Envelope

- Mission: fix the post-merge review findings on the repo quality audit baseline.
- Envelope: audit runner synthesis, regenerated baseline evidence, admin-doc freshness, and review handoff artifacts.
- Exclusions: no quality-policy promotion, no repo-wide lint cleanup, no manifest or mypy-baseline changes.

# Summary

- Fixed per-subsystem synthesis so each Python subsystem now carries its own artifact, counts, and representative examples instead of inheriting a shared combined output.
- Fixed exit-code handling so the audit matrix uses the tool footer written into each artifact rather than the wrapper shell's always-zero return code.
- Made the audit doc updaters idempotent for reruns, refreshed the environment report to record the actual interpreter used by the runner, removed stale combined Python artifacts, and regenerated the baseline summary from the corrected evidence.
- Revalidated the audit surface with focused tests, full `pytest runtime/tests -q`, `admin-structure-check`, and strategic corpus regeneration.

# Issue Catalogue

| ID | Finding | Disposition | Notes |
| --- | --- | --- | --- |
| IC-01 | Combined Python sweep results were being duplicated across `runtime`, `doc_steward`, `recursive_kernel`, and `project_builder`. | Resolved | The runner now captures and summarizes each governed Python target independently. |
| IC-02 | The audit wrapper wrote `EXIT_CODE=<tool>` into artifacts but the matrix trusted the wrapper process exit code `0`, making failing tools look green. | Resolved | `capture_command()` now prefers the appended footer, and passing rows no longer emit representative examples. |
| IC-03 | Audit reruns could rewrite admin docs for calendar reasons alone. | Resolved | The docs-index and tech-debt update helpers now preserve existing audit entries on rerun. |
| IC-04 | The environment report used `python --version` from `PATH` instead of the interpreter that actually executed the audit. | Resolved | The report now records `/home/linuxbrew/.linuxbrew/opt/python@3.14/bin/python3.14 --version` via the runner's interpreter binding. |

# Acceptance Criteria

| ID | Criterion | Status | Evidence Pointer | SHA-256 |
| --- | --- | --- | --- | --- |
| AC-01 | Audit runner captures per-subsystem Python evidence instead of duplicating a shared combined output. | PASS | scripts/workflow/run_quality_audit_baseline.py | 46b2d1498a8307b886c1c771c51617a9b4f4d8bb54a3325ea1b1de38e53e1ace |
| AC-02 | Audit matrix records actual tool exit codes and suppresses examples for passing rows. | PASS | artifacts/reports/quality_audit_baseline_v1/finding_matrix.json | 2825910be892dc67755cb6adfa7075d583d74536926bb495ec59041f684f3aa6 |
| AC-03 | Admin audit docs remain stable on rerun aside from intentional regenerated evidence. | PASS | docs/11_admin/QUALITY_AUDIT_BASELINE_v1.0.md | 7adb83a829a50acc9898bdcf9285f6bd612a1448e46042961c14c6e35cc6d9be |
| AC-04 | The environment artifact identifies the interpreter actually used by the audit run. | PASS | artifacts/reports/quality_audit_baseline_v1/environment.txt | 7c04f4f229c418250bcfa06c0763b9c450903dd24fb71d44b6946c1e8d008870 |
| AC-05 | Regression coverage exists for subsystem attribution, wrapper exit-code handling, and rerun idempotence. | PASS | runtime/tests/test_quality_audit_baseline.py | 78f68adf89e54bc57becdb53699ba4473336ccc454e6f9a37cef4fbaa1271826 |
| AC-06 | Stewardship follow-through completed for the touched docs. | PASS | docs/INDEX.md | 21e18ad8a4758a7447c3fcb2d1025bc4c1cf1a769b84f8b0e7161f6ba9795505 |

# Closure Evidence Checklist

| Item | Evidence | Verification |
| --- | --- | --- |
| Provenance | Worktree `fix/audit-baseline-review-fixes-v2` and this packet. | Verified against the current worktree diff and regenerated evidence bundle. |
| Artifacts | `artifacts/reports/quality_audit_baseline_v1/`, `docs/11_admin/QUALITY_AUDIT_BASELINE_v1.0.md`, and this review packet. | Present in the worktree and referenced above. |
| Repro | `pytest -q runtime/tests/test_quality_audit_baseline.py`, `pytest runtime/tests -q`, `python3 -m doc_steward.cli admin-structure-check .`, and `python3 docs/scripts/generate_strategic_context.py`. | Rerun after the fixes; all passed. |
| Governance | No protected governance paths were modified. | Verified from the changed-file set. |
| Outcome | Review findings corrected; regenerated audit evidence now matches the runner's actual behavior. | Ready for commit or closure. |

# Non-Goals

- This packet does not claim repo-wide quality debt is remediated.
- This packet does not promote any advisory tool to blocking mode.
- This packet does not change the governed scope of `opencode_governance` or root-level Markdown.

# Appendix

## Appendix A: Flattened Source, Docs, and Key Evidence

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
GOVERNED_PYTHON_TARGETS = (
    "runtime",
    "doc_steward",
    "recursive_kernel",
    "project_builder",
)


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
    effective_exit_code = extract_exit_code(combined)
    if effective_exit_code is None:
        effective_exit_code = proc.returncode
    return {
        "command": command,
        "output_path": str(output_path.relative_to(repo_root)),
        "exit_code": effective_exit_code,
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


def _python_audit_command(tool: str, target: str, report_path: Path) -> str:
    command_map = {
        "ruff_check": f"ruff check {target}",
        "ruff_format": f"ruff format --check {target}",
        "mypy": f"mypy {target}",
    }
    base_command = command_map[tool]
    return (
        f"{base_command} > {report_path} 2>&1; "
        f"code=$?; printf '\\nEXIT_CODE=%s\\n' \"$code\" >> {report_path}; exit 0"
    )


def audit_command_specs(report_dir: Path) -> list[CommandSpec]:
    specs: list[CommandSpec] = []
    for target in GOVERNED_PYTHON_TARGETS:
        specs.extend(
            [
                CommandSpec(
                    artifact_name=f"ruff_check_{target}.txt",
                    lane="python_style",
                    tool="ruff_check",
                    failure_class="ruff_error",
                    subsystem=target,
                    command=_python_audit_command(
                        "ruff_check", target, report_dir / f"ruff_check_{target}.txt"
                    ),
                ),
                CommandSpec(
                    artifact_name=f"ruff_format_{target}.txt",
                    lane="python_format",
                    tool="ruff_format",
                    failure_class="ruff_error",
                    subsystem=target,
                    command=_python_audit_command(
                        "ruff_format", target, report_dir / f"ruff_format_{target}.txt"
                    ),
                ),
                CommandSpec(
                    artifact_name=f"mypy_{target}.txt",
                    lane="python_types",
                    tool="mypy",
                    failure_class="mypy_error",
                    subsystem=target,
                    command=_python_audit_command(
                        "mypy", target, report_dir / f"mypy_{target}.txt"
                    ),
                ),
            ]
        )

    specs.extend(
        [
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
    )
    return specs


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
        rows.append(
            {
                "lane": spec.lane,
                "tool": spec.tool,
                "failure_class": spec.failure_class,
                "path_or_subsystem": spec.subsystem,
                "finding_count": finding_count(output, exit_code),
                "representative_examples": [] if exit_code == 0 else representative_examples(output),
                "exit_code": exit_code,
                "disposition": classify_disposition(spec.tool, spec.subsystem, exit_code, spec.notes),
                "recommended_owner": owner_for_subsystem(spec.subsystem),
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
        f"{PYTHON_EXE} --version",
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


def updated_docs_index_text(text: str) -> str:
    lines = text.splitlines()
    updated: list[str] = []
    inserted = False
    timestamp_updated = False
    row = "| [QUALITY_AUDIT_BASELINE_v1.0.md](./11_admin/QUALITY_AUDIT_BASELINE_v1.0.md) | **Audit baseline** — Repo-wide quality findings, evidence, and promotion recommendations |"
    row_present = "QUALITY_AUDIT_BASELINE_v1.0.md" in text
    for line in lines:
        if line.startswith("Last Updated: "):
            if not row_present:
                updated.append(f"Last Updated: {utc_date()}")
                timestamp_updated = True
            else:
                updated.append(line)
            continue
        updated.append(line)
        if "TECH_DEBT_INVENTORY.md" in line and not row_present:
            updated.append(row)
            inserted = True
    if not inserted and not row_present:
        updated.append("")
        updated.append(row)
    if inserted and not timestamp_updated:
        for idx, line in enumerate(updated):
            if line.startswith("Last Updated: "):
                updated[idx] = f"Last Updated: {utc_date()}"
                break
    return "\n".join(updated) + "\n"


def update_docs_index(repo_root: Path) -> None:
    path = repo_root / DOCS_INDEX_REL
    text = path.read_text(encoding="utf-8")
    _write_text(path, updated_docs_index_text(text))


def updated_tech_debt_inventory_text(text: str) -> str:
    section_header = "## Audit References"
    packet_label = "[QUALITY_AUDIT_BASELINE_v1.0.md](./QUALITY_AUDIT_BASELINE_v1.0.md)"
    if packet_label in text:
        return text if text.endswith("\n") else text + "\n"
    entry = (
        f"- {packet_label} — repo-wide quality baseline audit. "
        "Cross-reference Item 4 (Logging Inconsistency) and Item 5 "
        "(Validation Pattern Fragmentation) when triaging follow-up cleanup."
    )
    if section_header in text:
        text = text.replace(section_header, f"{section_header}\n\n{entry}", 1)
    else:
        marker = "---\n\n"
        insertion = f"---\n\n{section_header}\n\n{entry}\n\n"
        if marker in text:
            text = text.replace(marker, insertion, 1)
        else:
            text = f"{text.rstrip()}\n\n{section_header}\n\n{entry}\n"
    return text if text.endswith("\n") else text + "\n"


def update_tech_debt_inventory(repo_root: Path) -> None:
    path = repo_root / TECH_DEBT_REL
    text = path.read_text(encoding="utf-8")
    _write_text(path, updated_tech_debt_inventory_text(text))


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

from pathlib import Path

from scripts.workflow.run_quality_audit_baseline import (
    CommandSpec,
    append_exit_footer,
    build_finding_matrix,
    capture_command,
    classify_disposition,
    extract_exit_code,
    finding_count,
    known_pytest_failure,
    nonempty_lines,
    representative_examples,
    runtime_baseline_status,
    updated_docs_index_text,
    updated_tech_debt_inventory_text,
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


def test_capture_command_uses_appended_tool_exit_code(tmp_path: Path) -> None:
    output_path = tmp_path / "tool.txt"
    result = capture_command(
        tmp_path,
        f"printf 'problem\\n' > {output_path}; printf '\\nEXIT_CODE=7\\n' >> {output_path}; exit 0",
        output_path,
    )

    assert result["exit_code"] == 7
    assert extract_exit_code(str(result["output"])) == 7


def test_runtime_baseline_status_reports_timeout() -> None:
    output = "partial output\nTIMEOUT_SECONDS=300\nEXIT_CODE=124\n"
    assert runtime_baseline_status(output) == "timed out after 300 second(s) before first failure"


def test_runtime_baseline_status_reports_pass() -> None:
    assert runtime_baseline_status("ok\nEXIT_CODE=0\n") == "passed within audit budget"


def test_build_finding_matrix_keeps_subsystem_specific_output(tmp_path: Path) -> None:
    specs = [
        CommandSpec(
            artifact_name="ruff_check_runtime.txt",
            lane="python_style",
            tool="ruff_check",
            failure_class="ruff_error",
            subsystem="runtime",
            command="ruff check runtime",
        ),
        CommandSpec(
            artifact_name="ruff_check_doc_steward.txt",
            lane="python_style",
            tool="ruff_check",
            failure_class="ruff_error",
            subsystem="doc_steward",
            command="ruff check doc_steward",
        ),
    ]
    outputs = {
        "ruff_check_runtime.txt": {
            "exit_code": 1,
            "output": "runtime/file.py:1: error\nEXIT_CODE=1\n",
        },
        "ruff_check_doc_steward.txt": {
            "exit_code": 1,
            "output": "doc_steward/file.py:1: error\nEXIT_CODE=1\n",
        },
    }

    rows = build_finding_matrix(tmp_path, specs, outputs)

    assert rows[0]["path_or_subsystem"] == "runtime"
    assert rows[0]["representative_examples"] == ["runtime/file.py:1: error"]
    assert rows[1]["path_or_subsystem"] == "doc_steward"
    assert rows[1]["representative_examples"] == ["doc_steward/file.py:1: error"]


def test_build_finding_matrix_omits_examples_for_passing_rows(tmp_path: Path) -> None:
    specs = [
        CommandSpec(
            artifact_name="ruff_check_runtime.txt",
            lane="python_style",
            tool="ruff_check",
            failure_class="ruff_error",
            subsystem="runtime",
            command="ruff check runtime",
        )
    ]
    outputs = {
        "ruff_check_runtime.txt": {
            "exit_code": 0,
            "output": "informational output\nEXIT_CODE=0\n",
        }
    }

    rows = build_finding_matrix(tmp_path, specs, outputs)

    assert rows[0]["finding_count"] == 0
    assert rows[0]["representative_examples"] == []


def test_updated_docs_index_text_preserves_timestamp_when_row_exists() -> None:
    original = (
        "# Index\n\n"
        "Last Updated: 2026-03-28\n\n"
        "| Document | Purpose |\n"
        "|----------|---------|\n"
        "| [TECH_DEBT_INVENTORY.md](./11_admin/TECH_DEBT_INVENTORY.md) | Debt |\n"
        "| [QUALITY_AUDIT_BASELINE_v1.0.md](./11_admin/QUALITY_AUDIT_BASELINE_v1.0.md) | Audit |\n"
    )

    updated = updated_docs_index_text(original)

    assert updated == original


def test_updated_tech_debt_inventory_text_is_idempotent_when_reference_exists() -> None:
    original = (
        "# Tech Debt Inventory\n\n"
        "## Audit References\n\n"
        "- [QUALITY_AUDIT_BASELINE_v1.0.md](./QUALITY_AUDIT_BASELINE_v1.0.md) — repo-wide quality baseline audit.\n"
    )

    updated = updated_tech_debt_inventory_text(original)

    assert updated == original

```

### FILE: `docs/11_admin/QUALITY_AUDIT_BASELINE_v1.0.md`

```md
# Quality Audit Baseline v1.0

Generated: 2026-03-29T03:40:24.585552Z

## Why This Exists

LifeOS now has a real quality gate, but a gate only proves enforcement exists. This audit establishes where the repo already conforms, where debt is concentrated, and what can safely be promoted next without guessing.

## Environment

- Audit environment: Python venv + repo quality toolchain
- Quality doctor passed: `true`
- Tool availability rows: `7`

## Current Standard Conformance

- Repo-scope quality gate passed: `false`
- Summary: command timed out after 60 second(s)
- Advisory tools in current policy: `mypy, yamllint, shellcheck`

## Top Debt Clusters

- `runtime`: 4 failing lane(s) across mypy, pytest, ruff_check, ruff_format
- `doc_steward`: 3 failing lane(s) across mypy, ruff_check, ruff_format
- `recursive_kernel`: 3 failing lane(s) across mypy, ruff_check, ruff_format
- `project_builder`: 3 failing lane(s) across mypy, ruff_check, ruff_format
- `docs_semantic`: 3 failing lane(s) across doc_steward
- `opencode_governance`: 2 failing lane(s) across ruff_check, ruff_format
- `yaml_shell_json_misc`: 2 failing lane(s) across shellcheck, yamllint
- `scripts_root_config`: 1 failing lane(s) across biome

## Enforcement Chain

- Pre-commit installation status: `not_installed`
- Hook logic evidence: `artifacts/reports/quality_audit_baseline_v1/hook_gate_tests.txt`

## Scope Gaps and Differential Lanes

- Root Markdown outside current quality-gate scope: `955` file(s)
- `opencode_governance` is packaged in `pyproject.toml` but omitted from manifest python targets; audited separately as a manifest-scope gap.
- `biome check .` is broader than the day-to-day quality router and is used here for baseline signal collection.

## Runtime Baseline Context

- Runtime baseline status: `timed out after 300 second(s) before first failure`
- Runtime failures are contextual baseline evidence only and are not merged into the quality findings matrix.

## Promotion Guidance

- Blocking-ready buckets: `docs_semantic, scripts_root_config`
- Keep advisory for now: `doc_steward, docs_markdown_style, docs_semantic, project_builder, recursive_kernel, runtime, scripts_root_config, yaml_shell_json_misc`
- Exclude or rescope: `opencode_governance`
- Recommended follow-up order: core Python ruff cleanup, biome/docs markdown, yamllint/shellcheck promotion decision, mypy by package, manifest decision for `opencode_governance`, then any root-Markdown scope expansion.

## Evidence Bundle

- Raw outputs: `artifacts/reports/quality_audit_baseline_v1/`
- Findings matrix: `artifacts/reports/quality_audit_baseline_v1/finding_matrix.json`
- Policy conformance: `artifacts/reports/quality_audit_baseline_v1/quality_gate_repo.json`


```

### FILE: `docs/INDEX.md`

```md
# LifeOS Strategic Corpus [P26-02-28 (rev12)]

<!-- markdownlint-disable MD013 MD040 MD060 -->

Last Updated: 2026-03-29

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

### FILE: `artifacts/reports/quality_audit_baseline_v1/finding_matrix.json`

```json
[
  {
    "artifact": "artifacts/reports/quality_audit_baseline_v1/ruff_check_runtime.txt",
    "disposition": "advisory_keep",
    "exit_code": 1,
    "failure_class": "ruff_error",
    "finding_count": 24975,
    "lane": "python_style",
    "notes": "",
    "path_or_subsystem": "runtime",
    "recommended_owner": "runtime",
    "representative_examples": [
      "I001 [*] Import block is un-sorted or un-formatted",
      "--> runtime/__main__.py:1:1",
      "|",
      "1 | / import sys",
      "2 | | from runtime.cli import main"
    ],
    "tool": "ruff_check"
  },
  {
    "artifact": "artifacts/reports/quality_audit_baseline_v1/ruff_format_runtime.txt",
    "disposition": "advisory_keep",
    "exit_code": 1,
    "failure_class": "ruff_error",
    "finding_count": 462,
    "lane": "python_format",
    "notes": "",
    "path_or_subsystem": "runtime",
    "recommended_owner": "runtime",
    "representative_examples": [
      "Would reformat: runtime/agents/api.py",
      "Would reformat: runtime/agents/cli_dispatch.py",
      "Would reformat: runtime/agents/fixtures.py",
      "Would reformat: runtime/agents/health.py",
      "Would reformat: runtime/agents/logging.py"
    ],
    "tool": "ruff_format"
  },
  {
    "artifact": "artifacts/reports/quality_audit_baseline_v1/mypy_runtime.txt",
    "disposition": "advisory_keep",
    "exit_code": 1,
    "failure_class": "mypy_error",
    "finding_count": 265,
    "lane": "python_types",
    "notes": "",
    "path_or_subsystem": "runtime",
    "recommended_owner": "runtime",
    "representative_examples": [
      "runtime/util/detsort.py:21: error: Incompatible default for argument \"key\" (default has type \"None\", argument has type \"Callable[[Any], Any]\")  [assignment]",
      "runtime/util/detsort.py:21: note: PEP 484 prohibits implicit Optional. Accordingly, mypy has changed its default to no_implicit_optional=True",
      "runtime/util/detsort.py:21: note: Use https://github.com/hauntsaninja/no_implicit_optional to automatically upgrade your codebase",
      "runtime/governance/protected_paths.py:225: error: Incompatible return value type (got \"tuple[bool, str | None]\", expected \"tuple[bool, str]\")  [return-value]",
      "runtime/governance/protected_paths.py:230: error: Incompatible return value type (got \"tuple[bool, str | None]\", expected \"tuple[bool, str]\")  [return-value]"
    ],
    "tool": "mypy"
  },
  {
    "artifact": "artifacts/reports/quality_audit_baseline_v1/ruff_check_doc_steward.txt",
    "disposition": "advisory_keep",
    "exit_code": 1,
    "failure_class": "ruff_error",
    "finding_count": 558,
    "lane": "python_style",
    "notes": "",
    "path_or_subsystem": "doc_steward",
    "recommended_owner": "doc_steward",
    "representative_examples": [
      "F841 [*] Local variable `e` is assigned to but never used",
      "--> doc_steward/admin_archive_link_ban_validator.py:57:29",
      "|",
      "55 |         try:",
      "56 |             content = md_file.read_text(encoding=\"utf-8\")"
    ],
    "tool": "ruff_check"
  },
  {
    "artifact": "artifacts/reports/quality_audit_baseline_v1/ruff_format_doc_steward.txt",
    "disposition": "advisory_keep",
    "exit_code": 1,
    "failure_class": "ruff_error",
    "finding_count": 29,
    "lane": "python_format",
    "notes": "",
    "path_or_subsystem": "doc_steward",
    "recommended_owner": "doc_steward",
    "representative_examples": [
      "Would reformat: doc_steward/admin_archive_link_ban_validator.py",
      "Would reformat: doc_steward/admin_structure_validator.py",
      "Would reformat: doc_steward/archive_structure_validator.py",
      "Would reformat: doc_steward/artefact_index_validator.py",
      "Would reformat: doc_steward/cli.py"
    ],
    "tool": "ruff_format"
  },
  {
    "artifact": "artifacts/reports/quality_audit_baseline_v1/mypy_doc_steward.txt",
    "disposition": "advisory_keep",
    "exit_code": 1,
    "failure_class": "mypy_error",
    "finding_count": 6,
    "lane": "python_types",
    "notes": "",
    "path_or_subsystem": "doc_steward",
    "recommended_owner": "doc_steward",
    "representative_examples": [
      "runtime/util/canonical.py:170: error: Name \"Path\" is not defined  [name-defined]",
      "doc_steward/artefact_index_validator.py:17: error: Incompatible default for argument \"directory\" (default has type \"None\", argument has type \"str\")  [assignment]",
      "doc_steward/artefact_index_validator.py:17: note: PEP 484 prohibits implicit Optional. Accordingly, mypy has changed its default to no_implicit_optional=True",
      "doc_steward/artefact_index_validator.py:17: note: Use https://github.com/hauntsaninja/no_implicit_optional to automatically upgrade your codebase",
      "doc_steward/cli.py:220: error: Argument 2 to \"check_artefact_index\" has incompatible type \"Any | None\"; expected \"str\"  [arg-type]"
    ],
    "tool": "mypy"
  },
  {
    "artifact": "artifacts/reports/quality_audit_baseline_v1/ruff_check_recursive_kernel.txt",
    "disposition": "advisory_keep",
    "exit_code": 1,
    "failure_class": "ruff_error",
    "finding_count": 312,
    "lane": "python_style",
    "notes": "",
    "path_or_subsystem": "recursive_kernel",
    "recommended_owner": "recursive_kernel",
    "representative_examples": [
      "I001 [*] Import block is un-sorted or un-formatted",
      "--> recursive_kernel/autogate.py:1:1",
      "|",
      "1 | / from enum import Enum",
      "2 | | from typing import Dict, List"
    ],
    "tool": "ruff_check"
  },
  {
    "artifact": "artifacts/reports/quality_audit_baseline_v1/ruff_format_recursive_kernel.txt",
    "disposition": "advisory_keep",
    "exit_code": 1,
    "failure_class": "ruff_error",
    "finding_count": 9,
    "lane": "python_format",
    "notes": "",
    "path_or_subsystem": "recursive_kernel",
    "recommended_owner": "recursive_kernel",
    "representative_examples": [
      "Would reformat: recursive_kernel/autogate.py",
      "Would reformat: recursive_kernel/backlog_parser.py",
      "Would reformat: recursive_kernel/builder.py",
      "Would reformat: recursive_kernel/planner.py",
      "Would reformat: recursive_kernel/runner.py"
    ],
    "tool": "ruff_format"
  },
  {
    "artifact": "artifacts/reports/quality_audit_baseline_v1/mypy_recursive_kernel.txt",
    "disposition": "advisory_keep",
    "exit_code": 1,
    "failure_class": "mypy_error",
    "finding_count": 148,
    "lane": "python_types",
    "notes": "",
    "path_or_subsystem": "recursive_kernel",
    "recommended_owner": "recursive_kernel",
    "representative_examples": [
      "runtime/governance/protected_paths.py:225: error: Incompatible return value type (got \"tuple[bool, str | None]\", expected \"tuple[bool, str]\")  [return-value]",
      "runtime/governance/protected_paths.py:230: error: Incompatible return value type (got \"tuple[bool, str | None]\", expected \"tuple[bool, str]\")  [return-value]",
      "runtime/orchestration/loop/budgets.py:39: error: Incompatible default for argument \"config\" (default has type \"None\", argument has type \"BudgetConfig\")  [assignment]",
      "runtime/orchestration/loop/budgets.py:39: note: PEP 484 prohibits implicit Optional. Accordingly, mypy has changed its default to no_implicit_optional=True",
      "runtime/orchestration/loop/budgets.py:39: note: Use https://github.com/hauntsaninja/no_implicit_optional to automatically upgrade your codebase"
    ],
    "tool": "mypy"
  },
  {
    "artifact": "artifacts/reports/quality_audit_baseline_v1/ruff_check_project_builder.txt",
    "disposition": "advisory_keep",
    "exit_code": 1,
    "failure_class": "ruff_error",
    "finding_count": 680,
    "lane": "python_style",
    "notes": "",
    "path_or_subsystem": "project_builder",
    "recommended_owner": "project_builder",
    "representative_examples": [
      "I001 [*] Import block is un-sorted or un-formatted",
      "--> project_builder/agents/planner.py:1:1",
      "|",
      "1 | / import json",
      "2 | | import sqlite3"
    ],
    "tool": "ruff_check"
  },
  {
    "artifact": "artifacts/reports/quality_audit_baseline_v1/ruff_format_project_builder.txt",
    "disposition": "advisory_keep",
    "exit_code": 1,
    "failure_class": "ruff_error",
    "finding_count": 21,
    "lane": "python_format",
    "notes": "",
    "path_or_subsystem": "project_builder",
    "recommended_owner": "project_builder",
    "representative_examples": [
      "Would reformat: project_builder/agents/planner.py",
      "Would reformat: project_builder/config/governance.py",
      "Would reformat: project_builder/config/settings.py",
      "Would reformat: project_builder/context/injection.py",
      "Would reformat: project_builder/context/tokenizer.py"
    ],
    "tool": "ruff_format"
  },
  {
    "artifact": "artifacts/reports/quality_audit_baseline_v1/mypy_project_builder.txt",
    "disposition": "advisory_keep",
    "exit_code": 1,
    "failure_class": "mypy_error",
    "finding_count": 7,
    "lane": "python_types",
    "notes": "",
    "path_or_subsystem": "project_builder",
    "recommended_owner": "project_builder",
    "representative_examples": [
      "project_builder/sandbox/manifest.py:11: error: Name \"ManifestValidationError\" already defined (possibly by an import)  [no-redef]",
      "project_builder/sandbox/runner.py:19: error: Invalid base class  [misc]",
      "project_builder/orchestrator/routing.py:29: error: Argument 3 to \"log_event\" has incompatible type \"None\"; expected \"str\"  [arg-type]",
      "project_builder/orchestrator/missions.py:72: error: Argument 3 to \"log_event\" has incompatible type \"None\"; expected \"str\"  [arg-type]",
      "project_builder/orchestrator/missions.py:95: error: Argument 3 to \"log_event\" has incompatible type \"None\"; expected \"str\"  [arg-type]"
    ],
    "tool": "mypy"
  },
  {
    "artifact": "artifacts/reports/quality_audit_baseline_v1/ruff_check_opencode_governance.txt",
    "disposition": "exclude_or_rescope",
    "exit_code": 1,
    "failure_class": "ruff_error",
    "finding_count": 41,
    "lane": "python_style",
    "notes": "packaged_but_not_in_manifest",
    "path_or_subsystem": "opencode_governance",
    "recommended_owner": "opencode",
    "representative_examples": [
      "E501 Line too long (285 > 100)",
      "--> opencode_governance/service.py:4:101",
      "|",
      "2 | \u2026",
      "3 | \u2026"
    ],
    "tool": "ruff_check"
  },
  {
    "artifact": "artifacts/reports/quality_audit_baseline_v1/ruff_format_opencode_governance.txt",
    "disposition": "exclude_or_rescope",
    "exit_code": 1,
    "failure_class": "ruff_error",
    "finding_count": 3,
    "lane": "python_format",
    "notes": "packaged_but_not_in_manifest",
    "path_or_subsystem": "opencode_governance",
    "recommended_owner": "opencode",
    "representative_examples": [
      "Would reformat: opencode_governance/errors.py",
      "Would reformat: opencode_governance/service.py",
      "2 files would be reformatted, 1 file already formatted"
    ],
    "tool": "ruff_format"
  },
  {
    "artifact": "artifacts/reports/quality_audit_baseline_v1/mypy_opencode_governance.txt",
    "disposition": "exclude_or_rescope",
    "exit_code": 0,
    "failure_class": "mypy_error",
    "finding_count": 0,
    "lane": "python_types",
    "notes": "packaged_but_not_in_manifest",
    "path_or_subsystem": "opencode_governance",
    "recommended_owner": "opencode",
    "representative_examples": [],
    "tool": "mypy"
  },
  {
    "artifact": "artifacts/reports/quality_audit_baseline_v1/biome_repo.txt",
    "disposition": "advisory_keep",
    "exit_code": 1,
    "failure_class": "biome_error",
    "finding_count": 58,
    "lane": "js_json_style",
    "notes": "broader_than_quality_gate_routing",
    "path_or_subsystem": "scripts_root_config",
    "recommended_owner": "repo_hygiene",
    "representative_examples": [
      "biome.json:2:14 deserialize \u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501",
      "i The configuration schema version does not match the CLI version 2.4.9",
      "1 \u2502 {",
      "> 2 \u2502   \"$schema\": \"https://biomejs.dev/schemas/2.4.4/schema.json\",",
      "\u2502              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^"
    ],
    "tool": "biome"
  },
  {
    "artifact": "artifacts/reports/quality_audit_baseline_v1/markdownlint_docs.txt",
    "disposition": "advisory_keep",
    "exit_code": 123,
    "failure_class": "markdownlint_error",
    "finding_count": 13610,
    "lane": "docs_markdown_style",
    "notes": "",
    "path_or_subsystem": "docs_markdown_style",
    "recommended_owner": "doc_steward",
    "representative_examples": [
      "docs/.pending_root_files/PULL_REQUEST_TEMPLATE.md:32 error MD012/no-multiple-blanks Multiple consecutive blank lines [Expected: 1; Actual: 2]",
      "docs/00_foundations/Anti_Failure_Operational_Packet_v0.1.md:4:121 error MD013/line-length Line length [Expected: 120; Actual: 143]",
      "docs/00_foundations/Anti_Failure_Operational_Packet_v0.1.md:6:121 error MD013/line-length Line length [Expected: 120; Actual: 143]",
      "docs/00_foundations/Anti_Failure_Operational_Packet_v0.1.md:30:121 error MD013/line-length Line length [Expected: 120; Actual: 208]",
      "docs/00_foundations/Anti_Failure_Operational_Packet_v0.1.md:150:121 error MD013/line-length Line length [Expected: 120; Actual: 149]"
    ],
    "tool": "markdownlint"
  },
  {
    "artifact": "artifacts/reports/quality_audit_baseline_v1/yamllint_repo.txt",
    "disposition": "advisory_keep",
    "exit_code": 123,
    "failure_class": "yamllint_error",
    "finding_count": 754,
    "lane": "yaml_style",
    "notes": "",
    "path_or_subsystem": "yaml_shell_json_misc",
    "recommended_owner": "repo_hygiene",
    "representative_examples": [
      ".github/workflows/branch_housekeeping_delete_merged_validator_suite.yml",
      "95:121    error    line too long (125 > 120 characters)  (line-length)",
      "104:121   error    line too long (134 > 120 characters)  (line-length)",
      "106:121   error    line too long (154 > 120 characters)  (line-length)",
      ".github/workflows/build-entry-check.yml"
    ],
    "tool": "yamllint"
  },
  {
    "artifact": "artifacts/reports/quality_audit_baseline_v1/shellcheck_repo.txt",
    "disposition": "advisory_keep",
    "exit_code": 123,
    "failure_class": "shellcheck_error",
    "finding_count": 20,
    "lane": "shell_style",
    "notes": "",
    "path_or_subsystem": "yaml_shell_json_misc",
    "recommended_owner": "repo_hygiene",
    "representative_examples": [
      ".claude/skills/lifeos-workflow/skills/merge-concurrent-sprints/branch-audit.sh:6:25: note: Double quote to prevent globbing and word splitting. [SC2086]",
      ".claude/skills/lifeos-workflow/skills/merge-concurrent-sprints/branch-audit.sh:7:20: note: Double quote to prevent globbing and word splitting. [SC2086]",
      ".claude/skills/lifeos-workflow/skills/merge-concurrent-sprints/branch-audit.sh:8:43: note: Double quote to prevent globbing and word splitting. [SC2086]",
      ".claude/skills/lifeos-workflow/skills/merge-concurrent-sprints/branch-audit.sh:18:16: note: Double quote to prevent globbing and word splitting. [SC2086]",
      ".claude/skills/lifeos-workflow/skills/merge-concurrent-sprints/branch-audit.sh:22:14: note: Double quote to prevent globbing and word splitting. [SC2086]"
    ],
    "tool": "shellcheck"
  },
  {
    "artifact": "artifacts/reports/quality_audit_baseline_v1/doc_dap_validate.txt",
    "disposition": "blocking_ready",
    "exit_code": 0,
    "failure_class": "doc_semantic_error",
    "finding_count": 0,
    "lane": "docs_semantic",
    "notes": "",
    "path_or_subsystem": "docs_semantic",
    "recommended_owner": "doc_steward",
    "representative_examples": [],
    "tool": "doc_steward"
  },
  {
    "artifact": "artifacts/reports/quality_audit_baseline_v1/doc_index_check.txt",
    "disposition": "advisory_keep",
    "exit_code": 1,
    "failure_class": "doc_semantic_error",
    "finding_count": 14,
    "lane": "docs_semantic",
    "notes": "two_argument_validator",
    "path_or_subsystem": "docs_semantic",
    "recommended_owner": "doc_steward",
    "representative_examples": [
      "[FAILED] Index check failed (13 errors):",
      "* Indexed file missing: ./01_governance/Antigravity_Council_Review_Packet_Spec_v1.0.md",
      "* Indexed file missing: ./02_protocols/Document_Steward_Protocol_v1.0.md",
      "* Indexed file missing: ./02_protocols/Build_Handoff_Protocol_v1.0.md",
      "* Indexed file missing: ./02_protocols/lifeos_packet_schemas_v1.yaml"
    ],
    "tool": "doc_steward"
  },
  {
    "artifact": "artifacts/reports/quality_audit_baseline_v1/doc_link_check.txt",
    "disposition": "blocking_ready",
    "exit_code": 0,
    "failure_class": "doc_semantic_error",
    "finding_count": 0,
    "lane": "docs_semantic",
    "notes": "",
    "path_or_subsystem": "docs_semantic",
    "recommended_owner": "doc_steward",
    "representative_examples": [],
    "tool": "doc_steward"
  },
  {
    "artifact": "artifacts/reports/quality_audit_baseline_v1/doc_opencode_validate.txt",
    "disposition": "advisory_keep",
    "exit_code": 1,
    "failure_class": "doc_semantic_error",
    "finding_count": 1,
    "lane": "docs_semantic",
    "notes": "",
    "path_or_subsystem": "docs_semantic",
    "recommended_owner": "doc_steward",
    "representative_examples": [
      "[FAILED] Missing required directory: /mnt/c/Users/cabra/Projects/LifeOS/.worktrees/audit-baseline-review-fixes-v2/artifacts/opencode"
    ],
    "tool": "doc_steward"
  },
  {
    "artifact": "artifacts/reports/quality_audit_baseline_v1/doc_admin_structure_check.txt",
    "disposition": "blocking_ready",
    "exit_code": 0,
    "failure_class": "doc_semantic_error",
    "finding_count": 0,
    "lane": "docs_semantic",
    "notes": "",
    "path_or_subsystem": "docs_semantic",
    "recommended_owner": "doc_steward",
    "representative_examples": [],
    "tool": "doc_steward"
  },
  {
    "artifact": "artifacts/reports/quality_audit_baseline_v1/doc_admin_archive_link_ban_check.txt",
    "disposition": "blocking_ready",
    "exit_code": 0,
    "failure_class": "doc_semantic_error",
    "finding_count": 0,
    "lane": "docs_semantic",
    "notes": "",
    "path_or_subsystem": "docs_semantic",
    "recommended_owner": "doc_steward",
    "representative_examples": [],
    "tool": "doc_steward"
  },
  {
    "artifact": "artifacts/reports/quality_audit_baseline_v1/doc_freshness_check.txt",
    "disposition": "blocking_ready",
    "exit_code": 0,
    "failure_class": "doc_semantic_error",
    "finding_count": 0,
    "lane": "docs_semantic",
    "notes": "",
    "path_or_subsystem": "docs_semantic",
    "recommended_owner": "doc_steward",
    "representative_examples": [],
    "tool": "doc_steward"
  },
  {
    "artifact": "artifacts/reports/quality_audit_baseline_v1/doc_protocols_structure_check.txt",
    "disposition": "blocking_ready",
    "exit_code": 0,
    "failure_class": "doc_semantic_error",
    "finding_count": 0,
    "lane": "docs_semantic",
    "notes": "",
    "path_or_subsystem": "docs_semantic",
    "recommended_owner": "doc_steward",
    "representative_examples": [],
    "tool": "doc_steward"
  },
  {
    "artifact": "artifacts/reports/quality_audit_baseline_v1/doc_runtime_structure_check.txt",
    "disposition": "blocking_ready",
    "exit_code": 0,
    "failure_class": "doc_semantic_error",
    "finding_count": 0,
    "lane": "docs_semantic",
    "notes": "",
    "path_or_subsystem": "docs_semantic",
    "recommended_owner": "doc_steward",
    "representative_examples": [],
    "tool": "doc_steward"
  },
  {
    "artifact": "artifacts/reports/quality_audit_baseline_v1/doc_archive_structure_check.txt",
    "disposition": "blocking_ready",
    "exit_code": 0,
    "failure_class": "doc_semantic_error",
    "finding_count": 0,
    "lane": "docs_semantic",
    "notes": "",
    "path_or_subsystem": "docs_semantic",
    "recommended_owner": "doc_steward",
    "representative_examples": [],
    "tool": "doc_steward"
  },
  {
    "artifact": "artifacts/reports/quality_audit_baseline_v1/doc_docs_archive_link_ban_check.txt",
    "disposition": "blocking_ready",
    "exit_code": 0,
    "failure_class": "doc_semantic_error",
    "finding_count": 0,
    "lane": "docs_semantic",
    "notes": "",
    "path_or_subsystem": "docs_semantic",
    "recommended_owner": "doc_steward",
    "representative_examples": [],
    "tool": "doc_steward"
  },
  {
    "artifact": "artifacts/reports/quality_audit_baseline_v1/doc_artefact_index_check.txt",
    "disposition": "advisory_keep",
    "exit_code": 1,
    "failure_class": "doc_semantic_error",
    "finding_count": 29,
    "lane": "docs_semantic",
    "notes": "",
    "path_or_subsystem": "docs_semantic",
    "recommended_owner": "doc_steward",
    "representative_examples": [
      "[FAILED] Artefact index check failed (28 errors):",
      "* docs/01_governance/ARTEFACT_INDEX.json: Orphan active file not in index: docs/01_governance/ALIGNMENT_REVIEW_TEMPLATE_v1.0.md",
      "* docs/01_governance/ARTEFACT_INDEX.json: Orphan active file not in index: docs/01_governance/Antigravity_Council_Review_Packet_Spec_v1.1.md",
      "* docs/01_governance/ARTEFACT_INDEX.json: Orphan active file not in index: docs/01_governance/Antigrav_Output_Hygiene_Policy_v0.1.md",
      "* docs/01_governance/ARTEFACT_INDEX.json: Orphan active file not in index: docs/01_governance/ARTEFACT_INDEX_SCHEMA.md"
    ],
    "tool": "doc_steward"
  },
  {
    "artifact": "artifacts/reports/quality_audit_baseline_v1/doc_version_duplicate_scan.txt",
    "disposition": "blocking_ready",
    "exit_code": 0,
    "failure_class": "doc_semantic_error",
    "finding_count": 0,
    "lane": "docs_semantic",
    "notes": "",
    "path_or_subsystem": "docs_semantic",
    "recommended_owner": "doc_steward",
    "representative_examples": [],
    "tool": "doc_steward"
  },
  {
    "artifact": "artifacts/reports/quality_audit_baseline_v1/hook_gate_tests.txt",
    "disposition": "blocking_ready",
    "exit_code": 0,
    "failure_class": "enforcement_error",
    "finding_count": 0,
    "lane": "enforcement_chain",
    "notes": "",
    "path_or_subsystem": "scripts_root_config",
    "recommended_owner": "repo_hygiene",
    "representative_examples": [],
    "tool": "pytest"
  },
  {
    "artifact": "artifacts/reports/quality_audit_baseline_v1/pytest_fast_fail.txt",
    "disposition": "advisory_keep",
    "exit_code": 124,
    "failure_class": "runtime_baseline_error",
    "finding_count": 188,
    "lane": "runtime_baseline",
    "notes": "context_only",
    "path_or_subsystem": "runtime",
    "recommended_owner": "runtime",
    "representative_examples": [
      "============================= test session starts ==============================",
      "platform linux -- Python 3.14.2, pytest-8.4.2, pluggy-1.6.0",
      "rootdir: /mnt/c/Users/cabra/Projects/LifeOS/.worktrees/audit-baseline-review-fixes-v2",
      "configfile: pyproject.toml",
      "plugins: anyio-4.13.0, cov-4.1.0, asyncio-0.26.0"
    ],
    "tool": "pytest"
  }
]

```

### FILE: `artifacts/reports/quality_audit_baseline_v1/environment.txt`

```text
$ /tmp/quality_audit_venv/bin/python --version
Python 3.14.2
EXIT_CODE=0

$ ruff --version
ruff 0.15.8
EXIT_CODE=0

$ mypy --version
mypy 1.19.1 (compiled: yes)
EXIT_CODE=0

$ biome --version
Version: 2.4.9
EXIT_CODE=0

$ markdownlint --version
0.47.0
EXIT_CODE=0

$ yamllint --version
yamllint 1.38.0
EXIT_CODE=0

$ shellcheck --version
ShellCheck - shell script analysis tool
version: 0.11.0
license: GNU General Public License, version 3
website: https://www.shellcheck.net
EXIT_CODE=0

$ node --version
v25.2.1
EXIT_CODE=0

$ npm --version
11.6.2
EXIT_CODE=0

```
