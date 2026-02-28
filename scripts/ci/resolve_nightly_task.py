#!/usr/bin/env python3
"""
Resolve the next nightly task for the build loop CI workflow.

Resolution order:
1. Check artifacts/dispatch/inbox/ for pending orders (reuses DispatchEngine pattern).
2. If inbox is empty, pop the first pending entry from a curated queue file
   at artifacts/dispatch/nightly_queue.yaml and generate an ExecutionOrder.
3. If no queue or empty, exit 0 with a warning (workflow creates a "no tasks" issue).

Output: writes a valid ExecutionOrder YAML to the path specified by --output.
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]

sys.path.insert(0, str(REPO_ROOT))

from runtime.orchestration.dispatch.order import (
    ORDER_SCHEMA_VERSION,
    load_order,
)


def find_inbox_order(repo_root: Path) -> Path | None:
    inbox = repo_root / "artifacts" / "dispatch" / "inbox"
    if not inbox.is_dir():
        return None
    candidates = sorted(
        f for f in inbox.glob("*.yaml") if not f.name.endswith(".tmp")
    )
    return candidates[0] if candidates else None


def pop_queue_entry(repo_root: Path) -> dict | None:
    queue_path = repo_root / "artifacts" / "dispatch" / "nightly_queue.yaml"
    if not queue_path.is_file():
        return None

    with open(queue_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if not isinstance(data, list) or len(data) == 0:
        return None

    entry = data.pop(0)

    with open(queue_path, "w", encoding="utf-8") as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False)

    return entry


def generate_order(entry: dict) -> dict:
    now_dt = datetime.now(timezone.utc)
    now = now_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    task_ref = entry.get("task_ref", "nightly-task")
    order_id = f"nightly-{now_dt.strftime('%Y%m%d-%H%M%S')}"

    steps = entry.get("steps", [])
    if not steps:
        steps = [{"name": "execute", "role": "builder", "provider": "auto"}]

    return {
        "schema_version": ORDER_SCHEMA_VERSION,
        "order_id": order_id,
        "task_ref": task_ref,
        "created_at": now,
        "steps": steps,
        "constraints": entry.get("constraints", {
            "worktree": True,
            "max_duration_seconds": 2400,
            "scope_paths": [],
        }),
        "shadow": {"enabled": False, "provider": "codex"},
        "supervision": {"per_cycle_check": False},
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Resolve nightly build loop task")
    parser.add_argument(
        "--output", required=True, help="Path to write the resolved ExecutionOrder YAML"
    )
    parser.add_argument(
        "--repo-root", default=str(REPO_ROOT), help="Repository root"
    )
    args = parser.parse_args(argv)

    repo_root = Path(args.repo_root).resolve()
    output_path = Path(args.output)

    # Strategy 1: Check inbox for pending orders
    inbox_order = find_inbox_order(repo_root)
    if inbox_order:
        # Validate it before copying
        load_order(inbox_order)
        output_path.write_text(inbox_order.read_text(encoding="utf-8"), encoding="utf-8")
        print(f"resolved: inbox order {inbox_order.name}")
        return 0

    # Strategy 2: Pop from curated nightly queue
    entry = pop_queue_entry(repo_root)
    if entry:
        order_dict = generate_order(entry)
        output_path.write_text(
            yaml.dump(order_dict, default_flow_style=False, sort_keys=False),
            encoding="utf-8",
        )
        # Validate the generated order
        load_order(output_path)
        print(f"resolved: queue entry -> {order_dict['order_id']}")
        return 0

    # Strategy 3: No tasks available
    print("warning: no tasks available in inbox or queue")
    return 0


if __name__ == "__main__":
    sys.exit(main())
