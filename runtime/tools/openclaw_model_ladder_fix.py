#!/usr/bin/env python3
"""
Safe repair tool for OpenClaw model ladder configuration.
Creates backup, applies minimal fixes, generates audit capsule.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


EXECUTION_BASE = [
    "openai-codex/gpt-5.3-codex",
    "google-gemini-cli/gemini-3-flash-preview",
    "openrouter/pony-alpha",
]
THINKING_BASE = [
    "openai-codex/gpt-5.3-codex",
    "github-copilot/claude-opus-4.6",
    "openrouter/deepseek-v3.2",
]


def sha256_file(path: Path) -> str:
    """Compute SHA256 hash of a file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def redact_tokens(cfg: Dict[str, Any]) -> Dict[str, Any]:
    """Create a redacted copy of config for display (remove auth tokens)."""
    import copy
    redacted = copy.deepcopy(cfg)

    # Redact common token locations
    if isinstance(redacted, dict):
        for key in list(redacted.keys()):
            if any(x in key.lower() for x in ("token", "key", "secret", "password", "credential")):
                redacted[key] = "[REDACTED]"
            elif isinstance(redacted[key], dict):
                redacted[key] = redact_tokens(redacted[key])
            elif isinstance(redacted[key], list):
                redacted[key] = [redact_tokens(x) if isinstance(x, dict) else x for x in redacted[key]]

    return redacted


def apply_ladder_fixes(cfg: Dict[str, Any]) -> Tuple[Dict[str, Any], List[str]]:
    """
    Apply minimal fixes to config to satisfy ladder policy.
    Returns (fixed_config, changes_made).
    """
    changes: List[str] = []

    # Ensure agents.list exists
    if "agents" not in cfg:
        cfg["agents"] = {}
        changes.append("Created agents section")

    if "list" not in cfg["agents"]:
        cfg["agents"]["list"] = []
        changes.append("Created agents.list array")

    agents_list = cfg["agents"]["list"]

    # Helper to find or create an agent
    def ensure_agent(agent_id: str, ladder_base: List[str]) -> None:
        for agent in agents_list:
            if isinstance(agent, dict) and agent.get("id") == agent_id:
                # Agent exists, update its ladder if invalid
                model = agent.get("model", {})
                if not isinstance(model, dict):
                    agent["model"] = {}
                    model = agent["model"]
                    changes.append(f"{agent_id}: created model section")

                primary = model.get("primary")
                fallbacks = model.get("fallbacks", [])

                if primary != ladder_base[0]:
                    model["primary"] = ladder_base[0]
                    changes.append(f"{agent_id}: set primary to {ladder_base[0]}")

                if not isinstance(fallbacks, list) or not fallbacks:
                    model["fallbacks"] = ladder_base[1:]
                    changes.append(f"{agent_id}: set fallbacks to policy ladder")

                return

        # Agent doesn't exist, create it
        new_agent: Dict[str, Any] = {
            "id": agent_id,
            "model": {
                "primary": ladder_base[0],
                "fallbacks": ladder_base[1:],
            }
        }
        if agent_id == "think":
            new_agent["thinking"] = "extra_high"

        agents_list.append(new_agent)
        changes.append(f"{agent_id}: created agent with policy ladder")

    ensure_agent("main", EXECUTION_BASE)
    ensure_agent("quick", EXECUTION_BASE)
    ensure_agent("think", THINKING_BASE)

    return cfg, changes


def main() -> int:
    parser = argparse.ArgumentParser(description="Safe repair tool for OpenClaw model ladder configuration.")
    parser.add_argument("--config", default=str(Path.home() / ".openclaw" / "openclaw.json"))
    parser.add_argument("--dry-run", action="store_true", help="Show what would be changed without applying")
    args = parser.parse_args()

    config_path = Path(args.config).expanduser()

    if not config_path.exists():
        print(f"ERROR: Config file not found: {config_path}", file=sys.stderr)
        print(f"NEXT: Run 'openclaw onboard' to initialize configuration", file=sys.stderr)
        return 1

    print("=== OpenClaw Model Ladder Fix ===\n")
    print(f"Config: {config_path}")

    # Load current config
    try:
        cfg = json.loads(config_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"ERROR: Config is not valid JSON: {e}", file=sys.stderr)
        return 1

    # Compute before hash
    hash_before = sha256_file(config_path)
    print(f"SHA256 (before): {hash_before[:16]}...")

    # Apply fixes
    fixed_cfg, changes = apply_ladder_fixes(cfg)

    if not changes:
        print("\nNo changes needed - ladder configuration is valid.")
        return 0

    print("\nProposed changes:")
    for i, change in enumerate(changes, 1):
        print(f"  {i}. {change}")

    if args.dry_run:
        print("\nDRY RUN - no changes applied.")
        return 0

    # Create backup
    timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    backup_dir = config_path.parent / "backups"
    backup_dir.mkdir(exist_ok=True)
    backup_path = backup_dir / f"openclaw.json.{timestamp}.backup"

    shutil.copy2(config_path, backup_path)
    print(f"\nBackup created: {backup_path}")

    # Write fixed config atomically
    temp_path = config_path.with_suffix(".tmp")
    temp_path.write_text(json.dumps(fixed_cfg, indent=2, sort_keys=False), encoding="utf-8")
    temp_path.replace(config_path)

    # Compute after hash
    hash_after = sha256_file(config_path)
    print(f"SHA256 (after):  {hash_after[:16]}...")

    # Write audit capsule
    capsule_path = backup_dir / f"ladder_fix_{timestamp}.audit.json"
    audit = {
        "timestamp": timestamp,
        "config_path": str(config_path),
        "backup_path": str(backup_path),
        "sha256_before": hash_before,
        "sha256_after": hash_after,
        "changes": changes,
        "execution_ladder": EXECUTION_BASE,
        "thinking_ladder": THINKING_BASE,
    }
    capsule_path.write_text(json.dumps(audit, indent=2), encoding="utf-8")
    print(f"Audit capsule: {capsule_path}")

    print("\nFix applied successfully.")
    print("NEXT: Run 'coo models status' to verify ladder health")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
