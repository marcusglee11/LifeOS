#!/usr/bin/env python3
"""Pipeline certification runner for LifeOS production hardening."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
import time
import tomllib
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = REPO_ROOT / "config" / "certification_profiles.yaml"
OUTPUT_PATH = REPO_ROOT / "artifacts" / "status" / "pipeline_readiness.json"


@dataclass(frozen=True)
class CommandSpec:
    path: str
    profile: str
    command: list[str]
    kind: str
    bypass_addopts: bool = False


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_profiles(config_path: Path = CONFIG_PATH) -> dict[str, Any]:
    payload = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("certification_profiles.yaml must be a mapping")
    return payload


def suite_profile_map(config: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(entry["path"]): entry
        for entry in config.get("suites", [])
        if isinstance(entry, dict) and entry.get("path")
    }


def ignored_suites_from_pyproject(pyproject_path: Path = REPO_ROOT / "pyproject.toml") -> list[str]:
    payload = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
    addopts = payload.get("tool", {}).get("pytest", {}).get("ini_options", {}).get("addopts", [])
    ignored: list[str] = []
    for opt in addopts:
        if isinstance(opt, str) and opt.startswith("--ignore="):
            ignored.append(opt.split("=", 1)[1])
    return ignored


def build_profile_commands(profile: str) -> list[CommandSpec]:
    commands = [
        CommandSpec(
            path="runtime/tests",
            profile="local",
            command=[sys.executable, "-m", "pytest", "runtime/tests", "-q"],
            kind="pytest",
        )
    ]
    if profile in {"ci", "live"}:
        commands.extend(
            [
                CommandSpec(
                    path="tests_recursive/test_steward_runner.py",
                    profile="ci",
                    command=[sys.executable, "-m", "pytest", "tests_recursive/test_steward_runner.py", "-q"],
                    kind="pytest",
                    bypass_addopts=True,
                ),
                CommandSpec(
                    path="runtime/tests/test_isolated_smoke_test.py",
                    profile="ci",
                    command=[sys.executable, "-m", "pytest", "runtime/tests/test_isolated_smoke_test.py", "-q"],
                    kind="pytest",
                    bypass_addopts=True,
                ),
                CommandSpec(
                    path="runtime/tests/test_sandbox_remediation.py",
                    profile="ci",
                    command=[sys.executable, "-m", "pytest", "runtime/tests/test_sandbox_remediation.py", "-q"],
                    kind="pytest",
                    bypass_addopts=True,
                ),
                CommandSpec(
                    path="runtime/tests/test_demo_approval_determinism.py",
                    profile="ci",
                    command=[sys.executable, "-m", "pytest", "runtime/tests/test_demo_approval_determinism.py", "-q"],
                    kind="pytest",
                    bypass_addopts=True,
                ),
                CommandSpec(
                    path="scripts/run_certification_tests.py",
                    profile="ci",
                    command=[sys.executable, "scripts/run_certification_tests.py"],
                    kind="command",
                ),
            ]
        )
    if profile == "live":
        commands.extend(
            [
                CommandSpec(
                    path="runtime/tests/test_e2e_mission_cli.py",
                    profile="live",
                    command=[sys.executable, "-m", "pytest", "runtime/tests/test_e2e_mission_cli.py", "-q"],
                    kind="pytest",
                    bypass_addopts=True,
                ),
                CommandSpec(
                    path="runtime/tests/test_opencode_stage1_5_live.py",
                    profile="live",
                    command=[sys.executable, "-m", "pytest", "runtime/tests/test_opencode_stage1_5_live.py", "-q"],
                    kind="pytest",
                    bypass_addopts=True,
                ),
                CommandSpec(
                    path="runtime/tests/orchestration/coo/test_invoke_receipts.py",
                    profile="live",
                    command=[
                        sys.executable,
                        "-m",
                        "pytest",
                        "runtime/tests/orchestration/coo/test_invoke_receipts.py",
                        "-q",
                        "-k",
                        "propose",
                    ],
                    kind="pytest",
                    bypass_addopts=True,
                ),
                CommandSpec(
                    path="runtime/tests/orchestration/coo/test_commands.py",
                    profile="live",
                    command=[
                        sys.executable,
                        "-m",
                        "pytest",
                        "runtime/tests/orchestration/coo/test_commands.py",
                        "-q",
                        "-k",
                        "direct or propose",
                    ],
                    kind="pytest",
                    bypass_addopts=True,
                ),
            ]
        )
    return commands


def _command_with_pytest_overrides(spec: CommandSpec, junit_path: Path) -> list[str]:
    command = list(spec.command)
    if spec.kind == "pytest":
        if spec.bypass_addopts:
            command[3:3] = ["-o", "addopts="]
        command.extend(["--junitxml", str(junit_path)])
    return command


def _parse_junit_xml(path: Path) -> tuple[dict[str, int], list[dict[str, str]]]:
    root = ET.parse(path).getroot()
    testcases = root.findall(".//testcase")
    counts = {"passed": 0, "failed": 0, "skipped": 0}
    skips: list[dict[str, str]] = []

    for case in testcases:
        file_attr = case.attrib.get("file", "").replace("\\", "/")
        class_attr = case.attrib.get("classname", "")
        name_attr = case.attrib.get("name", "")
        class_name = class_attr.split(".")[-1] if class_attr else ""
        if file_attr and class_name and class_name != Path(file_attr).stem:
            nodeid = f"{file_attr}::{class_name}::{name_attr}"
        elif file_attr:
            nodeid = f"{file_attr}::{name_attr}"
        else:
            nodeid = f"{class_attr}::{name_attr}".strip(":")

        if case.find("skipped") is not None:
            counts["skipped"] += 1
            skipped = case.find("skipped")
            reason = skipped.attrib.get("message", "") if skipped is not None else ""
            skips.append({"test": nodeid, "reason": reason})
        elif case.find("failure") is not None or case.find("error") is not None:
            counts["failed"] += 1
        else:
            counts["passed"] += 1

    return counts, skips


def _normalize_nodeid(nodeid: str) -> str:
    normalized = nodeid.replace("\\", "/")
    if "::" not in normalized:
        return normalized

    head, *tail = normalized.split("::")
    if "/" in head:
        return "::".join([head, *tail])

    dotted_parts = head.split(".")
    if not dotted_parts:
        return normalized

    class_name = None
    if dotted_parts[-1] and dotted_parts[-1][0].isupper():
        class_name = dotted_parts.pop()

    candidate = "/".join(dotted_parts) + ".py"
    normalized_parts = [candidate]
    if class_name:
        normalized_parts.append(class_name)
    normalized_parts.extend(tail)
    return "::".join(normalized_parts)


def classify_skip(test_name: str, reason: str, config: dict[str, Any]) -> dict[str, str] | None:
    normalized_test_name = _normalize_nodeid(test_name)
    for entry in config.get("skipped_tests", []):
        if isinstance(entry, dict) and _normalize_nodeid(str(entry.get("test", ""))) == normalized_test_name:
            return {
                "test": test_name,
                "reason": reason,
                "classification": str(entry["classification"]),
            }
    for entry in config.get("skip_reason_patterns", []):
        pattern = str(entry.get("pattern", ""))
        if pattern and re.search(pattern, reason):
            return {
                "test": test_name,
                "reason": reason,
                "classification": str(entry["classification"]),
            }
    return None


def determine_state(profile: str, blocking: bool, non_blocking: bool, previous_state: str | None = None) -> str:
    if blocking:
        return "red"
    if profile == "local":
        return "candidate" if non_blocking else "prod_local"
    if profile == "ci":
        return "candidate" if non_blocking else "prod_ci"
    if previous_state == "prod_ci":
        return "prod_ci"
    return "candidate"


def run_suite(spec: CommandSpec) -> tuple[dict[str, Any], dict[str, int], list[dict[str, str]], bool]:
    with tempfile.NamedTemporaryFile(prefix="certify_", suffix=".xml", delete=False) as tmp:
        junit_path = Path(tmp.name)

    command = _command_with_pytest_overrides(spec, junit_path)
    started = time.monotonic()
    result = subprocess.run(
        command,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    elapsed = round(time.monotonic() - started, 3)

    counts = {"passed": 0, "failed": 0, "skipped": 0}
    observed_skips: list[dict[str, str]] = []
    parse_error: str | None = None
    if spec.kind == "pytest" and junit_path.exists():
        try:
            counts, observed_skips = _parse_junit_xml(junit_path)
        except ET.ParseError as exc:
            parse_error = f"Malformed JUnit XML for {spec.path}: {exc}"

    suite_result = {
        "path": spec.path,
        "profile": spec.profile,
        "status": "pass" if result.returncode == 0 and parse_error is None else "fail",
        "evidence": str(junit_path) if junit_path.exists() else None,
        "elapsed_s": elapsed,
    }
    if parse_error is not None:
        suite_result["parse_error"] = parse_error
    return suite_result, counts, observed_skips, result.returncode == 0 and parse_error is None


def current_worktree_clean() -> bool:
    result = subprocess.run(
        ["git", "status", "--short"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode == 0 and not result.stdout.strip()


def certify(profile: str) -> dict[str, Any]:
    config = load_profiles()
    profile_map = suite_profile_map(config)
    ignored = ignored_suites_from_pyproject()

    leaks: list[dict[str, str]] = []
    for ignored_path in ignored:
        if ignored_path not in profile_map:
            leaks.append(
                {
                    "id": "ignored_suite_drift",
                    "severity": "blocking",
                    "detail": f"{ignored_path} missing from config/certification_profiles.yaml",
                }
            )

    if not current_worktree_clean():
        leaks.append(
            {
                "id": "worktree_cleanliness",
                "severity": "blocking",
                "detail": "git status --short is not empty",
            }
        )

    previous_state = None
    live_status = "not_run"
    if OUTPUT_PATH.exists():
        try:
            previous = json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))
            previous_state = previous.get("state")
            live_status = previous.get("live_status", "not_run")
        except Exception:
            previous_state = None

    suite_results: list[dict[str, Any]] = []
    default_counts = {"passed": 0, "failed": 0, "skipped": 0}
    classified_skips: list[dict[str, str]] = []
    blocking = any(leak["severity"] == "blocking" for leak in leaks)
    non_blocking = False

    for spec in build_profile_commands(profile):
        suite_result, counts, observed_skips, passed = run_suite(spec)
        suite_results.append(suite_result)
        if spec.path == "runtime/tests":
            default_counts = counts
        if not passed:
            parse_error = suite_result.get("parse_error")
            detail = f"{spec.path} failed for profile {profile}"
            if isinstance(parse_error, str):
                detail = f"{detail} ({parse_error})"
            leaks.append(
                {
                    "id": "suite_failure",
                    "severity": "blocking",
                    "detail": detail,
                }
            )
            blocking = True

        for skip in observed_skips:
            classified = classify_skip(skip["test"], skip["reason"], config)
            if classified is None:
                leaks.append(
                    {
                        "id": "skipped_test_drift",
                        "severity": "blocking",
                        "detail": f"{skip['test']} has unclassified skip reason: {skip['reason']}",
                    }
                )
                blocking = True
                classified_skips.append(
                    {
                        "test": skip["test"],
                        "reason": skip["reason"],
                        "classification": "unclassified",
                    }
                )
            else:
                classified_skips.append(classified)
                if classified["classification"] in {"wip", "env_optional"}:
                    non_blocking = True

    if profile == "live":
        live_status = "fail" if blocking else "pass"

    state = determine_state(profile, blocking, non_blocking, previous_state=previous_state)
    payload = {
        "state": state,
        "profile": profile,
        "timestamp": _now_iso(),
        "live_status": live_status,
        "pytest_summary": default_counts,
        "suite_results": suite_results,
        "skipped_tests": classified_skips,
        "leaks": leaks,
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run pipeline certification profiles.")
    parser.add_argument("--profile", choices=("local", "ci", "live"), required=True)
    args = parser.parse_args(argv)

    payload = certify(args.profile)
    print(json.dumps(payload, indent=2, sort_keys=True))

    if args.profile == "local":
        return 0 if payload["state"] == "prod_local" else 1
    if args.profile == "ci":
        return 0 if payload["state"] == "prod_ci" else 1
    return 0 if payload["live_status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
