#!/usr/bin/env python3
"""
Static shape linter for OpenClaw instance profile JSON files.

Validates internal logical consistency without requiring the gateway or
comparing against ~/.openclaw/openclaw.json.

Used by scripts/hooks/pre-commit when instance profiles are staged.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List


def lint_instance_profile(profile: Dict[str, Any], path: str = "") -> List[str]:
    """Return a list of violation messages. Empty list = clean."""
    violations: List[str] = []
    prefix = f"{path}: " if path else ""

    instance_id = profile.get("instance_id")
    if not instance_id or not str(instance_id).strip():
        violations.append(f"{prefix}instance_id must be a non-empty string")

    sandbox_policy = profile.get("sandbox_policy")
    if sandbox_policy is not None:
        if not isinstance(sandbox_policy, dict):
            violations.append(f"{prefix}sandbox_policy must be an object")
        else:
            allowed_modes = sandbox_policy.get("allowed_modes")
            target_posture = str(sandbox_policy.get("target_posture") or "").strip()

            if allowed_modes is not None:
                if not isinstance(allowed_modes, list) or len(allowed_modes) == 0:
                    violations.append(f"{prefix}sandbox_policy.allowed_modes must be a non-empty list")
                else:
                    str_modes = [str(m) for m in allowed_modes]
                    # If target_posture is "unsandboxed", allowed_modes should include "off"
                    # and must not be only ["all"] (which requires full sandboxing)
                    if target_posture == "unsandboxed":
                        if "off" not in str_modes:
                            violations.append(
                                f"{prefix}target_posture=unsandboxed but allowed_modes={str_modes} "
                                f"does not include 'off' — mode 'off' is what 'unsandboxed' means"
                            )
                        if str_modes == ["all"]:
                            violations.append(
                                f"{prefix}target_posture=unsandboxed but allowed_modes=['all'] "
                                f"only permits full sandboxing — set to ['off'] for unsandboxed posture"
                            )

    return violations


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Lint an OpenClaw instance profile JSON for internal consistency."
    )
    parser.add_argument("profile", help="Path to instance profile JSON file")
    args = parser.parse_args(argv)

    path = Path(args.profile).expanduser()
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"ERROR: cannot read {path}: {exc}", file=sys.stderr)
        return 1

    if not isinstance(raw, dict):
        print(f"ERROR: {path} must contain a JSON object", file=sys.stderr)
        return 1

    violations = lint_instance_profile(raw, str(path))
    if violations:
        for v in violations:
            print(f"LINT ERROR: {v}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
