#!/usr/bin/env python3
"""Policy-layer certification harness for the OpenCode stewardship gate."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


REPO_ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = REPO_ROOT / "scripts" / "opencode_gate_policy.py"
EVIDENCE_RELATIVE_DIR = Path("artifacts/evidence/opencode_steward_certification")
REPORT_NAME = "CERTIFICATION_REPORT_v1_4.json"
SOURCE_REPORT_PATH = REPO_ROOT / EVIDENCE_RELATIVE_DIR / REPORT_NAME


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def log(message: str) -> None:
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] {message}")


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def make_json_task(files: list[str], action: str, instruction: str) -> str:
    return json.dumps({"files": files, "action": action, "instruction": instruction})


def run_command(
    argv: list[str],
    *,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
    check: bool = False,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        argv,
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        check=check,
    )


def load_policy_module(repo_root: Path):
    spec = importlib.util.spec_from_file_location("opencode_gate_policy", repo_root / POLICY_PATH.relative_to(REPO_ROOT))
    if spec is None or spec.loader is None:
        raise RuntimeError("Failed to load scripts/opencode_gate_policy.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@dataclass
class TestResult:
    id: str
    name: str
    status: str
    details: str
    timestamp: str


class TestRunner:
    def __init__(self, repo_root: Path, report_path: Path):
        self.repo_root = repo_root
        self.report_path = report_path
        self.policy = load_policy_module(repo_root)
        self.results: list[TestResult] = []

    def record_result(self, test_id: str, name: str, success: bool, details: str = "") -> None:
        status = "PASS" if success else "FAIL"
        log(f"Test {test_id}: {name} -> {status} {details}".rstrip())
        self.results.append(
            TestResult(
                id=test_id,
                name=name,
                status=status,
                details=details,
                timestamp=_now_iso(),
            )
        )

    def expect(self, test_id: str, name: str, predicate: Callable[[], tuple[bool, str]]) -> None:
        success, details = predicate()
        self.record_result(test_id, name, success, details)

    def test_input_json_valid(self) -> None:
        def check() -> tuple[bool, str]:
            task_json = make_json_task(["docs/internal/test.md"], "create", "Create a test file.")
            payload = json.loads(task_json)
            required = {"files", "action", "instruction"}
            success = required.issubset(payload) and payload["action"] == "create"
            return success, ""

        self.expect("T-INPUT-1", "Valid JSON Accepted", check)

    def test_input_freetext_rejected(self) -> None:
        def check() -> tuple[bool, str]:
            try:
                json.loads("Please update the docs")
            except json.JSONDecodeError:
                return True, ""
            return False, "free-text unexpectedly parsed as JSON"

        self.expect("T-INPUT-2", "Free-Text Rejected", check)

    def _expect_validation_failure(self, status: str, path: str, expected_reason: str) -> tuple[bool, str]:
        original_cwd = Path.cwd()
        try:
            os.chdir(self.repo_root)
            allowed, reason = self.policy.validate_operation(status, path, self.policy.MODE_STEWARD)
        finally:
            os.chdir(original_cwd)
        success = (not allowed) and reason == expected_reason
        return success, f"reason={reason}"

    def test_path_traversal_rejected(self) -> None:
        self.expect(
            "T-SEC-1",
            "Path Traversal Rejected",
            lambda: self._expect_validation_failure("M", "docs/../secrets.txt", self.policy.ReasonCode.PATH_TRAVERSAL_BLOCKED),
        )

    def test_absolute_path_rejected(self) -> None:
        self.expect(
            "T-SEC-2",
            "Absolute Path Rejected",
            lambda: self._expect_validation_failure("A", "C:/Windows/System32/test.txt", self.policy.ReasonCode.PATH_ABSOLUTE_BLOCKED),
        )

    def test_denylist_py_file(self) -> None:
        self.expect(
            "T-SEC-3",
            "Denylist *.py Rejected",
            lambda: self._expect_validation_failure("M", "docs/example.py", self.policy.ReasonCode.DENYLIST_EXT_BLOCKED),
        )

    def test_denylist_scripts(self) -> None:
        self.expect(
            "T-SEC-4",
            "Denylist scripts/** Rejected",
            lambda: self._expect_validation_failure("M", "scripts/test.md", self.policy.ReasonCode.DENYLIST_ROOT_BLOCKED),
        )

    def test_denylist_config(self) -> None:
        self.expect(
            "T-SEC-5",
            "Denylist config/** Rejected",
            lambda: self._expect_validation_failure("A", "config/settings.yaml", self.policy.ReasonCode.DENYLIST_ROOT_BLOCKED),
        )

    def test_denylist_gemini_md(self) -> None:
        self.expect(
            "T-SEC-6",
            "Denylist GEMINI.md Rejected",
            lambda: self._expect_validation_failure("M", "GEMINI.md", self.policy.ReasonCode.DENYLIST_FILE_BLOCKED),
        )

    def test_denylist_foundations(self) -> None:
        self.expect(
            "T-SEC-7",
            "Denylist Foundations Rejected",
            lambda: self._expect_validation_failure(
                "M",
                "docs/00_foundations/LifeOS_Constitution_v2.0.md",
                self.policy.ReasonCode.DENYLIST_ROOT_BLOCKED,
            ),
        )

    def test_evidence_readonly(self) -> None:
        self.expect(
            "T-SEC-8",
            "Evidence Read-Only Enforced",
            lambda: self._expect_validation_failure(
                "A",
                "artifacts/evidence/test.json",
                self.policy.ReasonCode.OUTSIDE_ALLOWLIST_BLOCKED,
            ),
        )

    def test_outside_allowed_roots(self) -> None:
        self.expect(
            "T-SEC-9",
            "Outside Allowed Roots Rejected",
            lambda: self._expect_validation_failure("M", "runtime/core.py", self.policy.ReasonCode.DENYLIST_EXT_BLOCKED),
        )

    def test_git_index_symlink_attack(self) -> None:
        def check() -> tuple[bool, str]:
            docs_dir = self.repo_root / "docs"
            ensure_dir(docs_dir)
            target_path = docs_dir / "target.md"
            target_path.write_text("target", encoding="utf-8")
            run_command(["git", "add", "docs/target.md"], cwd=self.repo_root)

            empty_hash = "e69de29bb2d1d6434b8b29ae775ad8c2e48c5391"
            link_path = "docs/symlink_attack.md"
            update = run_command(
                ["git", "update-index", "--add", "--cacheinfo", "120000", empty_hash, link_path],
                cwd=self.repo_root,
            )

            safe = False
            reason = "update-index failed"
            if update.returncode == 0:
                safe, reason = self.policy.check_symlink(link_path, str(self.repo_root))

            run_command(["git", "rm", "--cached", "--force", link_path], cwd=self.repo_root)
            run_command(["git", "rm", "--cached", "--force", "docs/target.md"], cwd=self.repo_root)
            target_path.unlink(missing_ok=True)

            success = update.returncode == 0 and (not safe) and reason == self.policy.ReasonCode.SYMLINK_BLOCKED
            return success, f"reason={reason}"

        self.expect("T-SEC-10", "Git Index Symlink (120000) Rejected", check)

    def test_clean_tree_start(self) -> None:
        def check() -> tuple[bool, str]:
            result = run_command(["git", "status", "--porcelain"], cwd=self.repo_root)
            dirty = [line for line in result.stdout.splitlines() if line and not line.startswith("??")]
            return len(dirty) == 0, f"dirty={dirty[:3]}"

        self.expect("T-GIT-1", "Clean Tree Start (Isolated)", check)

    def test_detect_blocked_ops(self) -> None:
        def check() -> tuple[bool, str]:
            parsed = [
                ("D", "docs/old.md"),
                ("R", "docs/old.md", "docs/new.md"),
                ("C", "docs/src.md", "docs/dst.md"),
            ]
            blocked = self.policy.detect_blocked_ops(parsed)
            expected = {
                ("docs/old.md", "delete", self.policy.ReasonCode.PH2_DELETE_BLOCKED),
                ("docs/old.md->docs/new.md", "rename", self.policy.ReasonCode.PH2_RENAME_BLOCKED),
                ("docs/src.md->docs/dst.md", "copy", self.policy.ReasonCode.PH2_COPY_BLOCKED),
            }
            return set(blocked) == expected, f"blocked={blocked}"

        self.expect("T-SEC-11", "Structural Ops Detected", check)

    def test_execute_diff_and_parse(self) -> None:
        def check() -> tuple[bool, str]:
            staged_path = self.repo_root / ".gitignore"
            original = staged_path.read_text(encoding="utf-8")
            staged_path.write_text(original + "\n# diff probe\n", encoding="utf-8")
            run_command(["git", "add", ".gitignore"], cwd=self.repo_root)
            parsed, mode, error = self.policy.execute_diff_and_parse(str(self.repo_root))
            run_command(["git", "checkout", "--", ".gitignore"], cwd=self.repo_root)
            success = error is None and mode == "LOCAL" and parsed == [("M", ".gitignore")]
            return success, f"mode={mode} error={error} parsed={parsed}"

        self.expect("T-SEC-12", "Diff Parse Local Mode", check)

    def test_truncate_and_hash(self) -> None:
        def check() -> tuple[bool, str]:
            content = "\n".join(f"line-{i}" for i in range(self.policy.LOG_MAX_LINES + 5))
            truncated, was_truncated = self.policy.truncate_log(content)
            sample_path = self.repo_root / "docs" / "hash_probe.md"
            sample_path.write_text("hash me", encoding="utf-8")
            digest = self.policy.compute_file_hash(str(sample_path))
            sample_path.unlink(missing_ok=True)
            success = was_truncated and "[TRUNCATED]" in truncated and digest["algorithm"] == "sha256"
            return success, f"hash={digest['hex'][:12]}"

        self.expect("T-SEC-13", "Evidence Helpers Work", check)

    def run_all(self) -> None:
        self.test_input_json_valid()
        self.test_input_freetext_rejected()
        self.test_path_traversal_rejected()
        self.test_absolute_path_rejected()
        self.test_denylist_py_file()
        self.test_denylist_scripts()
        self.test_denylist_config()
        self.test_denylist_gemini_md()
        self.test_denylist_foundations()
        self.test_evidence_readonly()
        self.test_outside_allowed_roots()
        self.test_git_index_symlink_attack()
        self.test_clean_tree_start()
        self.test_detect_blocked_ops()
        self.test_execute_diff_and_parse()
        self.test_truncate_and_hash()

    def write_report(self) -> Path:
        ensure_dir(self.report_path.parent)
        passed = sum(result.status == "PASS" for result in self.results)
        payload = {
            "suite_version": "1.4",
            "timestamp": _now_iso(),
            "isolation": "detached_worktree",
            "repo_root": str(self.repo_root),
            "total": len(self.results),
            "passed": passed,
            "failed": len(self.results) - passed,
            "results": [result.__dict__ for result in self.results],
        }
        self.report_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        return self.report_path


def setup_isolation(source_root: Path) -> Path:
    temp_dir = Path(tempfile.mkdtemp(prefix="lifeos_policy_cert_"))
    log(f"Creating detached worktree at {temp_dir}")
    worktree = run_command(
        ["git", "worktree", "add", "--quiet", "--detach", str(temp_dir), "HEAD"],
        cwd=source_root,
    )
    if worktree.returncode != 0:
        raise RuntimeError(f"git worktree add failed: {worktree.stderr.strip()}")
    shutil.copy2(source_root / POLICY_PATH.relative_to(REPO_ROOT), temp_dir / POLICY_PATH.relative_to(REPO_ROOT))
    config_email = run_command(["git", "config", "user.email", "cert@lifeos.local"], cwd=temp_dir)
    config_name = run_command(["git", "config", "user.name", "LifeOS Cert"], cwd=temp_dir)
    if config_email.returncode != 0 or config_name.returncode != 0:
        raise RuntimeError("failed to configure git identity in isolation repo")
    working_diff = run_command(["git", "diff", "--quiet", "--", str(POLICY_PATH.relative_to(REPO_ROOT))], cwd=temp_dir)
    if working_diff.returncode == 1:
        run_command(["git", "add", str(POLICY_PATH.relative_to(REPO_ROOT))], cwd=temp_dir)
        bootstrap_commit = run_command(
            ["git", "commit", "--quiet", "-m", "[test] sync live policy into isolated harness"],
            cwd=temp_dir,
        )
        if bootstrap_commit.returncode != 0:
            raise RuntimeError(f"failed to commit isolated bootstrap changes: {bootstrap_commit.stderr.strip()}")
    return temp_dir


def teardown_isolation(source_root: Path, temp_dir: Path, *, preserve: bool) -> None:
    if preserve:
        log(f"Preserving isolated evidence at {temp_dir}")
        return

    run_command(["git", "worktree", "remove", "--force", str(temp_dir)], cwd=source_root)

    def on_rm_error(func, path, _exc_info) -> None:
        try:
            os.chmod(path, stat.S_IWRITE)
            func(path)
        except OSError:
            pass

    shutil.rmtree(temp_dir, onerror=on_rm_error)


def mirror_report(source_report: Path, destination_report: Path) -> Path:
    ensure_dir(destination_report.parent)
    destination_report.write_text(source_report.read_text(encoding="utf-8"), encoding="utf-8")
    return destination_report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run policy-layer certification for the OpenCode gate.")
    parser.add_argument(
        "--preserve-isolation",
        action="store_true",
        help="Keep the detached worktree on success for debugging.",
    )
    args = parser.parse_args(argv)

    isolated_root = setup_isolation(REPO_ROOT)
    report_path = isolated_root / EVIDENCE_RELATIVE_DIR / REPORT_NAME
    runner = TestRunner(repo_root=isolated_root, report_path=report_path)

    exit_code = 1
    try:
        runner.run_all()
        report_file = runner.write_report()
        mirrored_report = mirror_report(report_file, SOURCE_REPORT_PATH)
        passed = sum(result.status == "PASS" for result in runner.results)
        log(f"Report saved to {report_file}")
        log(f"Canonical report saved to {mirrored_report}")
        log(f"Total: {len(runner.results)}, Passed: {passed}, Failed: {len(runner.results) - passed}")
        exit_code = 0 if passed == len(runner.results) else 1
        return exit_code
    finally:
        teardown_isolation(REPO_ROOT, isolated_root, preserve=args.preserve_isolation or exit_code != 0)


if __name__ == "__main__":
    raise SystemExit(main())
