#!/usr/bin/env python3
"""Validate ea_receipt.v0 proof artifacts for LifeOS issue #75."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


EXPECTED_SCHEMA = "ea_receipt.v0"
EXPECTED_ISSUE = "marcusglee11/LifeOS#75"
EXPECTED_EXECUTOR = "codex-cli"
EXPECTED_BRANCH = "proof/codex-ea-substrate-75"
WORKDIR_CLASSES = {"writable_temp_clone", "writable_worktree"}
STATUSES = {"success", "failure"}


def _is_non_empty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def validate_receipt(path: Path) -> tuple[str | None, list[str]]:
    errors: list[str] = []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        return None, [f"cannot read: {exc}"]
    except json.JSONDecodeError as exc:
        return None, [f"invalid json: {exc}"]

    if not isinstance(data, dict):
        return None, ["top-level value must be object"]

    if data.get("schema") != EXPECTED_SCHEMA:
        errors.append("schema must be ea_receipt.v0")
    if data.get("issue") != EXPECTED_ISSUE:
        errors.append("issue must be marcusglee11/LifeOS#75")
    if not _is_non_empty_string(data.get("attempt_id")):
        errors.append("attempt_id must be non-empty string")
    if data.get("executor") != EXPECTED_EXECUTOR:
        errors.append("executor must be codex-cli")
    if not _is_non_empty_string(data.get("workdir_path")):
        errors.append("workdir_path must be non-empty string")
    if data.get("workdir_class") not in WORKDIR_CLASSES:
        errors.append("workdir_class must be writable_temp_clone or writable_worktree")
    if data.get("branch") != EXPECTED_BRANCH:
        errors.append("branch must be proof/codex-ea-substrate-75")

    status = data.get("status")
    if status not in STATUSES:
        errors.append("status must be success or failure")

    commands = data.get("commands")
    if not isinstance(commands, list) or not commands:
        errors.append("commands must be non-empty array")
    elif not all(isinstance(item, str) for item in commands):
        errors.append("commands must contain only strings")

    inner_exit_codes = data.get("inner_exit_codes")
    if not isinstance(inner_exit_codes, list) or not inner_exit_codes:
        errors.append("inner_exit_codes must be non-empty array")
    elif not all(_is_int(item) for item in inner_exit_codes):
        errors.append("inner_exit_codes must contain only integers")
    elif status == "success" and any(code != 0 for code in inner_exit_codes):
        errors.append("success receipts require all inner_exit_codes equal 0")
    elif status == "failure":
        if not any(code != 0 for code in inner_exit_codes):
            errors.append("failure receipts require at least one non-zero inner_exit_code")
        if not _is_non_empty_string(data.get("failure_summary")):
            errors.append("failure receipts require non-empty failure_summary")

    completion_truth = data.get("completion_truth")
    if not isinstance(completion_truth, dict):
        errors.append("completion_truth must be object")
    else:
        for key in ("openclaw_used", "telegram_used", "local_tui_used"):
            if completion_truth.get(key) is not False:
                errors.append(f"completion_truth.{key} must be exactly false")

    if not isinstance(data.get("artifacts"), dict):
        errors.append("artifacts must be object")

    return status if isinstance(status, str) else None, errors


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("usage: validate_ea_receipt_v0.py <receipt> [<receipt> ...]", file=sys.stderr)
        return 2

    exit_code = 0
    for raw_path in argv[1:]:
        path = Path(raw_path)
        status, errors = validate_receipt(path)
        if errors:
            exit_code = 1
            for error in errors:
                print(f"INVALID {path} {error}", file=sys.stderr)
        else:
            print(f"VALID ea_receipt.v0 {path} status={status}")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
