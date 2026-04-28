#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from memory_lib import (
    AUTHORITY_CLASSES,
    AUTHORITY_IMPACTS,
    CLASSIFICATIONS,
    PROPOSED_ACTIONS,
    RECORD_KINDS,
    RETENTION_CLASSES,
    SCOPES,
    SENSITIVITIES,
    iso_now,
    repo_root,
    write_front_matter,
)


def choose(label: str, options: list[str], default: str | None = None) -> str:
    while True:
        suffix = f" [{default}]" if default else ""
        print(f"{label}{suffix}:")
        for index, option in enumerate(options, start=1):
            print(f"  {index}. {option}")
        raw = input("> ").strip()
        if not raw and default:
            return default
        if raw.isdigit() and 1 <= int(raw) <= len(options):
            return options[int(raw) - 1]
        if raw in options:
            return raw
        print("invalid choice")


def ask(label: str, default: str = "") -> str:
    suffix = f" [{default}]" if default else ""
    raw = input(f"{label}{suffix}: ").strip()
    return raw or default


def build_payload(
    args: argparse.Namespace, interactive: bool = True
) -> tuple[dict[str, object], str, Path]:
    now = iso_now()
    repo = repo_root(Path.cwd())
    mode = args.mode or (
        choose("record shell", ["candidate", "durable"], "candidate")
        if interactive
        else "candidate"
    )
    record_kind = args.record_kind or choose("record_kind", sorted(RECORD_KINDS), "fact")
    scope = args.scope or choose("scope", sorted(SCOPES), "global")
    sensitivity = args.sensitivity or choose("sensitivity", sorted(SENSITIVITIES), "internal")
    retention_class = args.retention_class or choose(
        "retention_class", sorted(RETENTION_CLASSES), "long"
    )
    title = args.title or ask("title", "Synthetic shell")
    slug = (title.lower().replace(" ", "-") or "memory-shell").replace("/", "-")

    if mode == "candidate":
        classification = args.classification or choose(
            "candidate classification",
            [
                "agent_memory_candidate",
                "shared_knowledge_candidate",
                "canonical_doctrine_candidate",
                "conflict_candidate",
            ],
            "agent_memory_candidate",
        )
        staging_status = (
            "conflict_candidate" if classification == "conflict_candidate" else "candidate_packet"
        )
        payload: dict[str, object] = {
            "candidate_id": args.record_id or f"CAND-{now[:10]}-{slug}",
            "source_agent": args.source_agent or ask("source_agent", "manual-wizard"),
            "source_packet_type": "manual_wizard",
            "source_packet_id": args.source_packet_id or f"wizard-{now}",
            "generated_utc": now,
            "proposed_action": args.proposed_action
            or choose("proposed_action", sorted(PROPOSED_ACTIONS), "create"),
            "proposed_record_kind": record_kind,
            "proposed_authority_class": args.authority_class
            or choose("proposed_authority_class", sorted(AUTHORITY_CLASSES), "agent_memory"),
            "scope": scope,
            "requires_human_review": True,
            "authority_impact": args.authority_impact
            or choose("authority_impact", sorted(AUTHORITY_IMPACTS), "low"),
            "personal_inference": False,
            "sensitivity": sensitivity,
            "retention_class": retention_class,
            "classification": classification,
            "staging_status": staging_status,
            "promotion_basis": "manual COO review required before durable write",
            "sources": [
                {
                    "source_type": "manual_note",
                    "locator": "manual wizard shell; replace before review",
                    "quoted_evidence": "synthetic shell placeholder, not durable memory",
                    "captured_utc": now,
                    "content_hash": "",
                    "commit_sha": "",
                }
            ],
            "summary": title,
            "payload": {"title": title, "record_kind": record_kind, "scope": scope},
        }
        target = repo / "knowledge-staging" / f"{slug}.md"
        body = "\nSynthetic candidate shell. Replace source evidence before COO disposition.\n"
        return payload, body, Path(args.output) if args.output else target

    payload = {
        "id": args.record_id or f"MEM-{now[:10]}-{slug}",
        "title": title,
        "record_kind": record_kind,
        "authority_class": args.authority_class or "agent_memory",
        "scope": scope,
        "sensitivity": sensitivity,
        "retention_class": retention_class,
        "lifecycle_state": "draft",
        "created_utc": now,
        "updated_utc": now,
        "review_after": "",
        "owner": "COO",
        "writer": "COO",
        "derived_from_candidate": False,
        "sources": [
            {
                "source_type": "manual_note",
                "locator": "manual wizard shell; replace before activation",
                "quoted_evidence": "synthetic shell placeholder, not durable memory",
                "captured_utc": now,
                "content_hash": "",
                "commit_sha": "",
            }
        ],
        "supersedes": [],
        "superseded_by": "",
        "conflicts": [],
        "write_receipts": [],
        "tags": ["synthetic-shell"],
    }
    if record_kind == "state":
        payload["state_subject"] = ask("state_subject", "replace-before-review")
        payload["state_observed_utc"] = now
    if scope == "agent":
        agent = args.agent or ask("agent", "agent-name")
        payload["agent"] = agent
        target = repo / "memory" / "agents" / agent / f"{slug}.md"
    else:
        family = "decisions" if record_kind == "decision" else f"{record_kind}s"
        family_map = {"facts": "projects", "rules": "workflows", "states": "projects"}
        target = repo / "memory" / family_map.get(family, family) / f"{slug}.md"
    body = "\nSynthetic durable shell. Replace source evidence before activation.\n"
    return payload, body, Path(args.output) if args.output else target


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Create Phase 1 memory/candidate shell.")
    parser.add_argument("--mode", choices=["candidate", "durable"])
    parser.add_argument("--title")
    parser.add_argument("--record-id")
    parser.add_argument("--record-kind", choices=sorted(RECORD_KINDS))
    parser.add_argument("--scope", choices=sorted(SCOPES))
    parser.add_argument("--agent")
    parser.add_argument("--sensitivity", choices=sorted(SENSITIVITIES))
    parser.add_argument("--retention-class", choices=sorted(RETENTION_CLASSES))
    parser.add_argument("--classification", choices=sorted(CLASSIFICATIONS))
    parser.add_argument("--authority-class", choices=sorted(AUTHORITY_CLASSES))
    parser.add_argument("--authority-impact", choices=sorted(AUTHORITY_IMPACTS))
    parser.add_argument("--proposed-action", choices=sorted(PROPOSED_ACTIONS))
    parser.add_argument("--source-agent")
    parser.add_argument("--source-packet-id")
    parser.add_argument("--output")
    args = parser.parse_args(argv)
    payload, body, output = build_payload(args, interactive=args.mode is None)
    output.parent.mkdir(parents=True, exist_ok=True)
    write_front_matter(output, payload, body)
    print(output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
