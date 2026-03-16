#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
from json import JSONDecodeError
from json import JSONDecoder
from pathlib import Path
from typing import Any, Dict, List, Sequence

OPENCLAW_BIN = "openclaw"
DEFAULT_POLICY = {
    "target_posture": "shared_ingress",
    "allowed_modes": ["all"],
    "require_session_sandboxed": True,
    "require_elevated_disabled": True,
}


def _load_json(path: Path) -> Dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def extract_json_object(text: str) -> Dict[str, Any]:
    decoder = JSONDecoder()
    start = 0
    while True:
        start = text.find("{", start)
        if start < 0:
            raise ValueError("sandbox explain output did not contain JSON")
        try:
            obj, _end = decoder.raw_decode(text[start:])
        except JSONDecodeError:
            start += 1
            continue
        if isinstance(obj, dict):
            return obj
        start += 1


def _load_instance_policy(instance_profile: Dict[str, Any]) -> Dict[str, Any]:
    raw = instance_profile.get("sandbox_policy") or {}
    if not isinstance(raw, dict):
        raw = {}
    allowed_modes = raw.get("allowed_modes")
    if not isinstance(allowed_modes, list) or not allowed_modes:
        allowed_modes = list(DEFAULT_POLICY["allowed_modes"])
    return {
        "target_posture": str(raw.get("target_posture") or DEFAULT_POLICY["target_posture"]),
        "allowed_modes": [str(item) for item in allowed_modes if str(item).strip()],
        "require_session_sandboxed": bool(
            raw.get("require_session_sandboxed", DEFAULT_POLICY["require_session_sandboxed"])
        ),
        "require_elevated_disabled": bool(
            raw.get("require_elevated_disabled", DEFAULT_POLICY["require_elevated_disabled"])
        ),
    }


def _read_sandbox_payload(sandbox_explain_file: Path | None, openclaw_bin: str) -> Dict[str, Any]:
    if sandbox_explain_file is not None:
        return extract_json_object(sandbox_explain_file.read_text(encoding="utf-8", errors="replace"))

    proc = subprocess.run(
        [openclaw_bin, "sandbox", "explain", "--json"],
        capture_output=True,
        check=False,
        text=True,
        timeout=20,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"sandbox explain failed with exit code {proc.returncode}")
    return extract_json_object(proc.stdout)


def assert_sandbox_policy(
    config: Dict[str, Any],
    instance_profile: Dict[str, Any],
    sandbox_payload: Dict[str, Any],
) -> Dict[str, Any]:
    del config

    policy = _load_instance_policy(instance_profile)
    sandbox = sandbox_payload.get("sandbox") or {}
    elevated = sandbox_payload.get("elevated") or {}
    if not isinstance(sandbox, dict) or not isinstance(elevated, dict):
        raise ValueError("sandbox explain JSON missing sandbox/elevated objects")

    observed_mode = str(sandbox.get("mode") or "unknown").strip() or "unknown"
    session_is_sandboxed = bool(sandbox.get("sessionIsSandboxed"))
    elevated_enabled = bool(elevated.get("enabled"))

    violations: List[str] = []
    if observed_mode not in policy["allowed_modes"]:
        violations.append("sandbox_mode_disallowed")
    if policy["require_session_sandboxed"] and not session_is_sandboxed:
        violations.append("sandbox_session_not_sandboxed")
    if policy["require_elevated_disabled"] and elevated_enabled:
        violations.append("sandbox_elevated_enabled")

    return {
        "policy_ok": len(violations) == 0,
        "target_posture": policy["target_posture"],
        "allowed_modes": policy["allowed_modes"],
        "observed_mode": observed_mode,
        "session_is_sandboxed": session_is_sandboxed,
        "elevated_enabled": elevated_enabled,
        "workspace_root": str(sandbox.get("workspaceRoot") or ""),
        "violations": violations,
    }


def _render_text(result: Dict[str, Any]) -> str:
    lines = [
        f"sandbox_policy_ok={'true' if result['policy_ok'] else 'false'}",
        f"target_posture={result['target_posture']}",
        f"allowed_modes={','.join(result['allowed_modes'])}",
        f"observed_mode={result['observed_mode']}",
        f"session_is_sandboxed={'true' if result['session_is_sandboxed'] else 'false'}",
        f"elevated_enabled={'true' if result['elevated_enabled'] else 'false'}",
        f"workspace_root={result['workspace_root']}",
        f"violations={','.join(result['violations'])}",
    ]
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Assert OpenClaw sandbox policy for COO startup.")
    parser.add_argument("--config", required=True)
    parser.add_argument("--instance-profile", required=True)
    parser.add_argument("--sandbox-explain-file", default="")
    parser.add_argument("--openclaw-bin", default=OPENCLAW_BIN)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    config = _load_json(Path(args.config).expanduser())
    instance_profile = _load_json(Path(args.instance_profile).expanduser())
    sandbox_file = Path(args.sandbox_explain_file).expanduser() if args.sandbox_explain_file else None

    try:
        sandbox_payload = _read_sandbox_payload(sandbox_file, args.openclaw_bin)
        result = assert_sandbox_policy(config, instance_profile, sandbox_payload)
    except Exception as exc:
        policy = _load_instance_policy(instance_profile)
        result = {
            "policy_ok": False,
            "target_posture": policy["target_posture"],
            "allowed_modes": policy["allowed_modes"],
            "observed_mode": "unknown",
            "session_is_sandboxed": False,
            "elevated_enabled": False,
            "workspace_root": "",
            "violations": ["sandbox_explain_parse_failed"],
            "error": f"{type(exc).__name__}:{exc}",
        }

    if args.json:
        print(json.dumps(result, sort_keys=True, separators=(",", ":"), ensure_ascii=True))
    else:
        print(_render_text(result))
        if "error" in result:
            print(f"error={result['error']}")
    return 0 if result["policy_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
