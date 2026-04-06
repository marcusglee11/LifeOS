#!/usr/bin/env python3
"""Emit a sprint_close_packet.v1 for wrapper-driven agent handoff."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def _parse_csv(raw: str) -> list[str]:
    return [item.strip() for item in raw.split(",") if item.strip()]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", required=True, help="Repository root for packet output")
    parser.add_argument("--python-root", default="", help="Python import root if different from --repo-root")
    parser.add_argument("--order-id", required=True, help="Dispatch order ID")
    parser.add_argument("--task-ref", required=True, help="Backlog task reference")
    parser.add_argument("--agent", required=True, help="Agent id (codex|claude_code|gemini|opencode)")
    parser.add_argument("--outcome", required=True, help="Packet outcome")
    parser.add_argument("--sync-check-result", default="skipped", help="Sync-check result summary")
    parser.add_argument("--evidence-paths", default="", help="Comma-separated evidence paths")
    parser.add_argument("--open-items", default="", help="Comma-separated open items")
    parser.add_argument(
        "--suggested-next-task-ids",
        default="",
        help="Comma-separated suggested next task ids",
    )
    parser.add_argument("--state-mutations", default="", help="Comma-separated state mutations")
    args = parser.parse_args()

    repo_root = Path(args.repo_root)
    python_root = Path(args.python_root) if args.python_root else repo_root
    if str(python_root) not in sys.path:
        sys.path.insert(0, str(python_root))

    from runtime.orchestration.coo.closures import write_sprint_close_packet

    try:
        path = write_sprint_close_packet(
            repo_root=repo_root,
            order_id=args.order_id,
            task_ref=args.task_ref,
            agent=args.agent,
            outcome=args.outcome,
            evidence_paths=_parse_csv(args.evidence_paths),
            open_items=_parse_csv(args.open_items),
            suggested_next_task_ids=_parse_csv(args.suggested_next_task_ids),
            state_mutations=_parse_csv(args.state_mutations),
            sync_check_result=args.sync_check_result,
        )
    except Exception as exc:  # pragma: no cover - exercised by subprocess tests
        print(f"[emit_sprint_close_packet] error: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1

    print(f"[emit_sprint_close_packet] packet written: {path}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
