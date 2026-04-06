#!/usr/bin/env python3
"""
Two-file config drift checker: compares ~/.openclaw/openclaw.json against
the in-repo instance profile to detect mismatches that would block coo start.

Does NOT require the gateway to be running.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List


def _load_json(path: Path) -> Dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def _resolve_sandbox_mode(config: Dict[str, Any]) -> str:
    """
    Extract the effective sandbox mode for the main agent from openclaw.json.

    Priority: agents.list[id=main].sandbox.mode > agents.defaults.sandbox.mode > "off"
    """
    agents = config.get("agents") or {}

    # Check agents.list for a main-agent override
    agent_list = agents.get("list") or []
    if isinstance(agent_list, list):
        for agent in agent_list:
            if isinstance(agent, dict) and agent.get("id") == "main":
                sb = agent.get("sandbox") or {}
                mode = sb.get("mode")
                if mode is not None:
                    return str(mode)
    elif isinstance(agent_list, dict):
        main_agent = agent_list.get("main") or {}
        sb = main_agent.get("sandbox") or {}
        mode = sb.get("mode")
        if mode is not None:
            return str(mode)

    # Fall back to agents.defaults
    defaults = agents.get("defaults") or {}
    sb = defaults.get("sandbox") or {}
    mode = sb.get("mode")
    if mode is not None:
        return str(mode)

    return "off"


def _has_docker_config(config: Dict[str, Any]) -> bool:
    """Return True if any agent has sandbox.docker.* configured."""
    agents = config.get("agents") or {}

    agent_list = agents.get("list") or []
    if isinstance(agent_list, list):
        for agent in agent_list:
            if isinstance(agent, dict):
                sb = agent.get("sandbox") or {}
                if sb.get("docker"):
                    return True
    elif isinstance(agent_list, dict):
        for agent in agent_list.values():
            if isinstance(agent, dict):
                sb = agent.get("sandbox") or {}
                if sb.get("docker"):
                    return True

    defaults = agents.get("defaults") or {}
    if (defaults.get("sandbox") or {}).get("docker"):
        return True

    return False


def check_config_pair(
    config: Dict[str, Any],
    instance_profile: Dict[str, Any],
) -> Dict[str, Any]:
    sandbox_policy = instance_profile.get("sandbox_policy") or {}
    allowed_modes: List[str] = [
        str(m) for m in (sandbox_policy.get("allowed_modes") or [])
    ]

    sandbox_mode = _resolve_sandbox_mode(config)
    docker_dead_config = (
        sandbox_mode == "off" and _has_docker_config(config)
    )
    sandbox_mode_allowed = sandbox_mode in allowed_modes if allowed_modes else True

    violations: List[str] = []
    if not sandbox_mode_allowed:
        violations.append("sandbox_mode_disallowed")
    if docker_dead_config:
        violations.append("docker_dead_config")

    return {
        "pair_check_ok": len(violations) == 0,
        "sandbox_mode": sandbox_mode,
        "allowed_modes": allowed_modes,
        "sandbox_mode_allowed": sandbox_mode_allowed,
        "docker_dead_config": docker_dead_config,
        "violations": violations,
    }


def _render_text(result: Dict[str, Any]) -> str:
    lines = [
        f"pair_check_ok={'true' if result['pair_check_ok'] else 'false'}",
        f"sandbox_mode={result['sandbox_mode']}",
        f"allowed_modes={','.join(result['allowed_modes'])}",
        f"sandbox_mode_allowed={'true' if result['sandbox_mode_allowed'] else 'false'}",
        f"docker_dead_config={'true' if result['docker_dead_config'] else 'false'}",
        f"violations={','.join(result['violations'])}",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Check drift between openclaw.json and an instance profile."
    )
    parser.add_argument("--config", required=True, help="Path to openclaw.json")
    parser.add_argument("--instance-profile", required=True, help="Path to instance profile JSON")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args(argv)

    config_path = Path(args.config).expanduser()
    profile_path = Path(args.instance_profile).expanduser()

    try:
        config = _load_json(config_path)
        instance_profile = _load_json(profile_path)
        result = check_config_pair(config, instance_profile)
    except Exception as exc:
        result = {
            "pair_check_ok": False,
            "sandbox_mode": "unknown",
            "allowed_modes": [],
            "sandbox_mode_allowed": False,
            "docker_dead_config": False,
            "violations": ["parse_failed"],
            "error": f"{type(exc).__name__}:{exc}",
        }

    if args.json:
        print(json.dumps(result, sort_keys=True, separators=(",", ":"), ensure_ascii=True))
    else:
        print(_render_text(result))
        if "error" in result:
            print(f"error={result['error']}")

    return 0 if result["pair_check_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
