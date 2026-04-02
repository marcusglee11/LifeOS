#!/usr/bin/env python3
"""Ops lane certification runner for constrained operational autonomy."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from runtime.orchestration.ops.registry import get_action_spec


REPO_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = REPO_ROOT / "config" / "ops" / "lanes.yaml"
OUTPUT_PATH = REPO_ROOT / "artifacts" / "status" / "ops_readiness.json"


@dataclass(frozen=True)
class CommandSpec:
    lane_id: str
    profile: str
    command: list[str]
    evidence_path: str


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_lanes(config_path: Path = CONFIG_PATH) -> dict[str, Any]:
    payload = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("ops lanes config must be a mapping")
    return payload


def _parse_junit_counts(path: Path) -> dict[str, int]:
    root = ET.parse(path).getroot()
    counts = {"passed": 0, "failed": 0, "skipped": 0}
    for case in root.findall(".//testcase"):
        if case.find("skipped") is not None:
            counts["skipped"] += 1
        elif case.find("failure") is not None or case.find("error") is not None:
            counts["failed"] += 1
        else:
            counts["passed"] += 1
    return counts


def current_worktree_clean() -> bool:
    result = subprocess.run(
        ["git", "status", "--short"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode == 0 and not result.stdout.strip()


def build_profile_commands(profile: str, lanes_payload: dict[str, Any]) -> list[CommandSpec]:
    commands: list[CommandSpec] = []
    for lane in lanes_payload.get("lanes", []):
        if not isinstance(lane, dict):
            continue
        lane_id = str(lane.get("lane_id", "")).strip()
        if not lane_id:
            continue
        profile_payload = (lane.get("profiles") or {}).get(profile) or {}
        for suite in profile_payload.get("required_suites", []):
            if not isinstance(suite, str) or not suite.strip():
                continue
            commands.append(
                CommandSpec(
                    lane_id=lane_id,
                    profile=profile,
                    command=[sys.executable, "-m", "pytest", suite, "-q", "-o", "addopts="],
                    evidence_path=suite,
                )
            )
    return commands


def determine_state(
    profile: str,
    blocking: bool,
    previous_state: str | None = None,
) -> str:
    if blocking:
        return "red"
    if profile == "local":
        return "prod_local"
    if profile == "ci":
        return "prod_ci"
    if previous_state == "prod_ci":
        return "prod_ci"
    return "candidate"


def validate_lane_manifest(lanes_payload: dict[str, Any]) -> list[dict[str, str]]:
    leaks: list[dict[str, str]] = []
    for lane in lanes_payload.get("lanes", []):
        if not isinstance(lane, dict):
            leaks.append(
                {
                    "id": "lane_manifest_shape",
                    "severity": "blocking",
                    "detail": "each lane must be a mapping",
                }
            )
            continue
        lane_id = str(lane.get("lane_id", "")).strip() or "<unknown>"
        approval_class = str(lane.get("approval_class", "")).strip()
        if approval_class != "explicit_human_approval":
            leaks.append(
                {
                    "id": "lane_approval_class",
                    "severity": "blocking",
                    "detail": f"{lane_id} must use explicit_human_approval in the initial envelope",
                }
            )
        allowed_actions = lane.get("allowed_actions") or []
        excluded_actions = set(lane.get("excluded_actions") or [])
        overlap = excluded_actions.intersection(allowed_actions)
        if overlap:
            leaks.append(
                {
                    "id": "lane_action_overlap",
                    "severity": "blocking",
                    "detail": f"{lane_id} overlaps allowed/excluded actions: {sorted(overlap)}",
                }
            )
        for action_id in allowed_actions:
            try:
                spec = get_action_spec(str(action_id))
            except Exception:
                leaks.append(
                    {
                        "id": "lane_unknown_action",
                        "severity": "blocking",
                        "detail": f"{lane_id} references unsupported action_id {action_id!r}",
                    }
                )
                continue
            if not spec.requires_approval:
                leaks.append(
                    {
                        "id": "lane_approval_policy",
                        "severity": "blocking",
                        "detail": f"{lane_id} action {action_id!r} is not approval-gated",
                    }
                )
    return leaks


def run_suite(spec: CommandSpec) -> tuple[dict[str, Any], dict[str, int], bool]:
    with tempfile.NamedTemporaryFile(prefix="ops_certify_", suffix=".xml", delete=False) as tmp:
        junit_path = Path(tmp.name)

    command = [*spec.command, f"--junitxml={junit_path}"]
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
    parse_error = None
    if junit_path.exists():
        try:
            counts = _parse_junit_counts(junit_path)
        except ET.ParseError as exc:
            parse_error = str(exc)

    suite_result = {
        "lane_id": spec.lane_id,
        "profile": spec.profile,
        "path": spec.evidence_path,
        "status": "pass" if result.returncode == 0 and parse_error is None else "fail",
        "elapsed_s": elapsed,
        "evidence": str(junit_path) if junit_path.exists() else None,
    }
    if parse_error is not None:
        suite_result["parse_error"] = parse_error
    if result.stderr:
        suite_result["stderr"] = result.stderr.strip()
    return suite_result, counts, result.returncode == 0 and parse_error is None


def certify(profile: str) -> dict[str, Any]:
    lanes_payload = load_lanes()
    leaks = validate_lane_manifest(lanes_payload)
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
    pytest_summary = {"passed": 0, "failed": 0, "skipped": 0}
    blocking = any(leak["severity"] == "blocking" for leak in leaks)

    for spec in build_profile_commands(profile, lanes_payload):
        suite_result, counts, passed = run_suite(spec)
        suite_results.append(suite_result)
        for key in pytest_summary:
            pytest_summary[key] += counts[key]
        if not passed:
            blocking = True
            leaks.append(
                {
                    "id": "suite_failure",
                    "severity": "blocking",
                    "detail": f"{spec.evidence_path} failed for ops profile {profile}",
                }
            )

    if not current_worktree_clean():
        blocking = True
        leaks.append(
            {
                "id": "worktree_cleanliness_post_run",
                "severity": "blocking",
                "detail": "git status --short is not empty after ops profile suites completed",
            }
        )

    if profile == "live":
        live_status = "fail" if blocking else "pass"

    state = determine_state(profile, blocking, previous_state=previous_state)
    payload = {
        "schema_version": "ops_readiness.v1",
        "state": state,
        "profile": profile,
        "timestamp": _now_iso(),
        "live_status": live_status,
        "lane_manifest": lanes_payload,
        "pytest_summary": pytest_summary,
        "suite_results": suite_results,
        "leaks": leaks,
    }
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run ops certification profiles.")
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
