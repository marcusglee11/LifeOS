#!/usr/bin/env python3
"""Validate the LifeOS agent-control-plane external contract pin manifest."""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml

REQUIRED_SOURCE = {
    "repo": "marcusglee11/agent-control-plane",
    "url": "https://github.com/marcusglee11/agent-control-plane",
}
PIN_RE = re.compile(r"^[0-9a-f]{40}$")


def _fail(message: str) -> int:
    print(f"FAIL: {message}", file=sys.stderr)
    return 1


def _load_manifest(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise ValueError("manifest root must be a mapping")
    return data


def _git_cat_file(source_worktree: Path, commit: str, source_path: str) -> bool:
    proc = subprocess.run(
        ["git", "-C", str(source_worktree), "cat-file", "-e", f"{commit}:{source_path}"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    return proc.returncode == 0


def validate_manifest(
    manifest: dict[str, Any], repo_root: Path, source_worktree: Path | None = None
) -> list[str]:
    errors: list[str] = []

    if manifest.get("schema_version") != "external_contract_pin.v1":
        errors.append("schema_version must be external_contract_pin.v1")
    if manifest.get("name") != "agent-control-plane":
        errors.append("name must be agent-control-plane")
    if manifest.get("status") != "active":
        errors.append("status must be active")

    source = manifest.get("source")
    if not isinstance(source, dict):
        errors.append("source must be a mapping")
        source = {}

    for key, expected in REQUIRED_SOURCE.items():
        if source.get(key) != expected:
            errors.append(f"source.{key} must be {expected}")

    commit = source.get("pinned_commit")
    if not isinstance(commit, str) or not PIN_RE.fullmatch(commit):
        errors.append("source.pinned_commit must be a 40-character lowercase hex SHA")
        commit = ""

    branch = source.get("branch")
    if not isinstance(branch, str) or not branch:
        errors.append("source.branch must be set")

    artifacts = manifest.get("consumed_artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        errors.append("consumed_artifacts must be a non-empty list")
        artifacts = []

    for idx, artifact in enumerate(artifacts):
        prefix = f"consumed_artifacts[{idx}]"
        if not isinstance(artifact, dict):
            errors.append(f"{prefix} must be a mapping")
            continue
        source_path = artifact.get("source_path")
        if not isinstance(source_path, str) or not source_path:
            errors.append(f"{prefix}.source_path must be set")
            continue
        if source_path.startswith("/") or ".." in Path(source_path).parts:
            errors.append(f"{prefix}.source_path must be repository-relative")
        local_path = artifact.get("local_path")
        if local_path not in (None, ""):
            local = repo_root / str(local_path)
            if not local.exists():
                errors.append(f"{prefix}.local_path does not exist: {local_path}")
        if source_worktree is not None and commit:
            if not _git_cat_file(source_worktree, commit, source_path):
                errors.append(f"{prefix}.source_path not found at pinned commit: {source_path}")

    update_policy = manifest.get("update_policy")
    if not isinstance(update_policy, dict):
        errors.append("update_policy must be a mapping")
    else:
        compatibility = update_policy.get("compatibility_check")
        if not isinstance(compatibility, dict) or not compatibility.get("command"):
            errors.append("update_policy.compatibility_check.command must be set")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manifest",
        default="config/external_contracts/agent_control_plane_pin.yaml",
        help="Path to the external contract pin manifest.",
    )
    parser.add_argument(
        "--source-worktree",
        help=(
            "Optional local agent-control-plane git worktree for pinned artifact existence checks."
        ),
    )
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[2]
    manifest_path = (repo_root / args.manifest).resolve()
    source_worktree = Path(args.source_worktree).resolve() if args.source_worktree else None

    try:
        manifest = _load_manifest(manifest_path)
    except Exception as exc:  # noqa: BLE001 - CLI should print parse failures tersely.
        return _fail(f"could not load manifest: {exc}")

    if source_worktree is not None and not (source_worktree / ".git").exists():
        return _fail(f"source worktree is not a git checkout: {source_worktree}")

    errors = validate_manifest(manifest, repo_root, source_worktree)
    if errors:
        for error in errors:
            print(f"FAIL: {error}", file=sys.stderr)
        return 1

    source = manifest["source"]
    print(
        "OK: agent-control-plane pin valid "
        f"repo={source['repo']} branch={source['branch']} commit={source['pinned_commit']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
