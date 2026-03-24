#!/usr/bin/env python3
"""
Safe repair tool for OpenClaw model ladder configuration.
Creates backup, applies minimal fixes, generates audit capsule.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from runtime.util.canonical import sha256_file


EXECUTION_BASE = [
    "openai-codex/gpt-5.3-codex",
    "openai-codex/gpt-5.1",
    "openai-codex/gpt-5.1-codex-max",
]
THINKING_BASE = list(EXECUTION_BASE)




def apply_ladder_fixes(cfg: Dict[str, Any]) -> Tuple[Dict[str, Any], List[str]]:
    """
    Apply minimal fixes to config to satisfy ladder policy.
    Returns (fixed_config, changes_made).
    """
    changes: List[str] = []

    def normalize_fallbacks(current_fallbacks: Any, required_prefix: List[str]) -> List[str]:
        if not isinstance(current_fallbacks, list):
            current_fallbacks = []
        existing = [str(x) for x in current_fallbacks if isinstance(x, str) and str(x).strip()]
        filtered_existing = [
            x
            for x in existing
            if ("haiku" not in x.lower()) and ("small" not in x.lower()) and (not x.lower().startswith("claude-max/"))
        ]
        extras = [x for x in filtered_existing if x not in required_prefix]
        return required_prefix + extras

    # Ensure agents section exists
    if "agents" not in cfg or not isinstance(cfg.get("agents"), dict):
        cfg["agents"] = {}
        changes.append("Created agents section")

    agents = cfg["agents"]

    # Ensure agents.defaults.model exists and follows policy.
    defaults = agents.get("defaults")
    if not isinstance(defaults, dict):
        agents["defaults"] = {}
        defaults = agents["defaults"]
        changes.append("Created agents.defaults section")

    defaults_model = defaults.get("model")
    if not isinstance(defaults_model, dict):
        defaults["model"] = {}
        defaults_model = defaults["model"]
        changes.append("Created agents.defaults.model section")

    if defaults_model.get("primary") != EXECUTION_BASE[0]:
        defaults_model["primary"] = EXECUTION_BASE[0]
        changes.append(f"agents.defaults: set primary to {EXECUTION_BASE[0]}")

    normalized_defaults_fallbacks = normalize_fallbacks(defaults_model.get("fallbacks"), EXECUTION_BASE[1:])
    if defaults_model.get("fallbacks") != normalized_defaults_fallbacks:
        defaults_model["fallbacks"] = normalized_defaults_fallbacks
        changes.append("agents.defaults: normalized fallback prefix to subscription-first ladder")

    # Ensure agents.list exists
    if "list" not in agents:
        agents["list"] = []
        changes.append("Created agents.list array")

    agents_list = agents["list"]

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

                required_prefix = ladder_base[1:]
                normalized_fallbacks = normalize_fallbacks(fallbacks, required_prefix)
                current_fallbacks = fallbacks if isinstance(fallbacks, list) else []
                if current_fallbacks != normalized_fallbacks:
                    model["fallbacks"] = normalized_fallbacks
                    changes.append(f"{agent_id}: normalized fallback prefix to subscription-first ladder")

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
    parser.add_argument(
        "--config",
        default=os.environ.get("OPENCLAW_CONFIG_PATH", str(Path.home() / ".openclaw" / "openclaw.json")),
    )
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
