#!/usr/bin/env python3
"""
package_context.py - Generate context packs for agent roles.

Usage:
    python docs/scripts/package_context.py --for {architect|council|builder} --component "<name>" --mode {0|1|2}
    python docs/scripts/package_context.py --for council --artefact <review_packet_path>
    python docs/scripts/package_context.py --resume --component "<name>"
    python docs/scripts/package_context.py --for council --component "<name>" --allow-provisional
"""

import argparse
import hashlib
import os
import re
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List

import yaml

# Paths
REPO_ROOT = Path(__file__).parent.parent.parent
WORKSTREAMS_PATH = REPO_ROOT / "artifacts" / "workstreams.yaml"
STATE_PATH = REPO_ROOT / "docs" / "11_admin" / "LIFEOS_STATE.md"
PACKETS_BASE = REPO_ROOT / "artifacts" / "packets"
REVIEW_PACKETS = REPO_ROOT / "artifacts" / "review_packets"

# Canonical governance refs
PROTECTED_PATHS_POLICY_REF = "config/governance/protected_artefacts.json"
COUNCIL_PROMPTS_DIR = REPO_ROOT / "docs" / "09_prompts" / "v1.0" / "roles"
COUNCIL_PROCEDURE_REFS = [
    "docs/99_archive/legacy_structures/Specs/council/Council_Protocol_v1.0.md",
    "docs/01_governance/Council_Invocation_Runtime_Binding_Spec_v1.0.md",
]

# Caps per role
CAPS = {
    "architect": {"goal_summary": 5, "constraints": 12, "success_criteria": 10, "refs": 5},
    "builder": {"goal_summary": 5, "constraints": 10, "success_criteria": 5, "refs": 5},
    "council": {"decision_questions": 5, "refs": 5},
}

# Default TTL
DEFAULT_TTL_HOURS = 72


def normalize_repo_path(path) -> str:
    """Normalize path to forward-slash repo-style path.
    
    Converts Windows backslashes to forward slashes for portable,
    deterministic refs that work across platforms.
    """
    return str(path).replace('\\', '/')


def load_workstreams() -> dict:
    """Load workstreams.yaml."""
    if not WORKSTREAMS_PATH.exists():
        return {}
    return yaml.safe_load(WORKSTREAMS_PATH.read_text(encoding="utf-8")) or {}


def resolve_component_to_slug(component_name: str, allow_provisional: bool = False) -> Optional[str]:
    """Resolve human component name to workstream slug.
    
    By default, fails closed if component is not found. Use allow_provisional=True
    to auto-propose a new workstream entry.
    """
    workstreams = load_workstreams()
    component_lower = component_name.lower().strip()
    
    matches = []
    for slug, data in workstreams.items():
        # Exact match on human name
        if data.get("component_human_name", "").lower() == component_lower:
            matches.append(slug)
            continue
        # Alias match
        aliases = data.get("aliases", [])
        for alias in aliases:
            if alias.lower() == component_lower:
                matches.append(slug)
                break
    
    if len(matches) == 1:
        return matches[0]
    elif len(matches) > 1:
        print(f"BLOCKED: Ambiguous component '{component_name}' matches: {matches}", file=sys.stderr)
        emit_blocked_packet(component_name, f"Ambiguous component matches: {matches}")
        return None
    
    # Component not found
    if not allow_provisional:
        print(f"BLOCKED: Unknown component '{component_name}'. Use --allow-provisional to auto-add.", file=sys.stderr)
        emit_blocked_packet(component_name, f"Unknown component '{component_name}'. Not in workstreams.yaml.")
        return None
    
    # Auto-propose with --allow-provisional flag
    slug = re.sub(r'[^a-z0-9]+', '_', component_lower).strip('_')
    workstreams[slug] = {
        "component_human_name": component_name,
        "status": "PROVISIONAL",
        "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "description": f"Auto-proposed workstream for {component_name}",
        "aliases": [],
    }
    WORKSTREAMS_PATH.write_text(yaml.dump(workstreams, sort_keys=True), encoding="utf-8")
    print(f"INFO: Auto-proposed workstream '{slug}' for '{component_name}'", file=sys.stderr)
    return slug


def emit_blocked_packet(component: str, reason: str) -> None:
    """Emit a BLOCKED packet for fail-closed scenarios."""
    blocked_dir = PACKETS_BASE / "blocked"
    blocked_dir.mkdir(parents=True, exist_ok=True)
    
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    slug = re.sub(r'[^a-z0-9]+', '_', component.lower()).strip('_') or "unknown"
    
    packet = {
        "packet_type": "BLOCKED",
        "packet_id": str(uuid.uuid4()),
        "component": component,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "blocked": {
            "owner": "Builder",
            "reason": reason,
            "unblock_condition": "Add component to artifacts/workstreams.yaml or use --allow-provisional",
        }
    }
    
    path = blocked_dir / f"BLOCKED_{slug}_{ts}.yaml"
    path.write_text(yaml.dump(packet, sort_keys=False), encoding="utf-8")
    print(f"Emitted BLOCKED: {path}", file=sys.stderr)


def truncate_list(items: list, cap: int, marker: str = "[TRUNCATED]") -> list:
    """Truncate list to cap, adding marker if truncated."""
    if len(items) <= cap:
        return items
    return items[:cap - 1] + [marker]


def truncate_text(text: str, max_lines: int) -> str:
    """Truncate text to max lines, adding marker if truncated."""
    lines = text.strip().split('\n')
    if len(lines) <= max_lines:
        return text
    return '\n'.join(lines[:max_lines - 1]) + '\n[TRUNCATED]'


def find_last_review_packet(slug: str) -> Optional[Path]:
    """Find most recent review packet for a workstream."""
    if not REVIEW_PACKETS.exists():
        return None
    
    # Look for packets matching the component name pattern
    workstreams = load_workstreams()
    component_name = workstreams.get(slug, {}).get("component_human_name", slug)
    pattern = component_name.replace(" ", "_")
    
    matches = sorted(
        [p for p in REVIEW_PACKETS.glob("*.md") if pattern.lower() in p.name.lower()],
        key=lambda x: x.stat().st_mtime,
        reverse=True
    )
    return matches[0] if matches else None


def extract_goal_from_state() -> str:
    """Extract Current Focus from LIFEOS_STATE.md."""
    if not STATE_PATH.exists():
        return "No LIFEOS_STATE.md found"
    
    content = STATE_PATH.read_text(encoding="utf-8")
    match = re.search(r'## Current Focus\s*\n+(.+?)(?=\n##|\Z)', content, re.DOTALL)
    if match:
        return match.group(1).strip()[:500]
    return "Current focus not found"


def generate_packet_id() -> str:
    """Generate a UUID for packet_id."""
    return str(uuid.uuid4())


def now_iso() -> str:
    """Current time in ISO 8601."""
    return datetime.now(timezone.utc).isoformat()


def discover_council_role_prompts() -> List[str]:
    """Discover canonical council role prompt files, ordered lexicographically."""
    if not COUNCIL_PROMPTS_DIR.exists():
        return []
    
    prompts = sorted([
        normalize_repo_path(p.relative_to(REPO_ROOT))
        for p in COUNCIL_PROMPTS_DIR.glob("*.md")
        if p.is_file()
    ])
    return prompts


def discover_council_procedure_refs() -> List[str]:
    """Return canonical council procedure refs, ordered lexicographically."""
    refs = []
    for ref in sorted(COUNCIL_PROCEDURE_REFS):
        path = REPO_ROOT / ref
        if path.exists():
            refs.append(ref)
    return refs


def write_packet(packet: dict, packet_type: str, slug: str) -> Path:
    """Write packet to artifacts/packets/<type>/ and update current pointer."""
    # Determine output directory
    type_dir_map = {
        "ARCHITECT_CONTEXT_PACKET": "architect_context",
        "BUILDER_CONTEXT_PACKET": "builder_context",
        "COUNCIL_REVIEW_PACKET": "council_context",
    }
    type_dir = type_dir_map.get(packet_type, packet_type.lower())
    output_dir = PACKETS_BASE / type_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Filename with timestamp
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = f"{packet_type}_{slug}_{ts}.yaml"
    output_path = output_dir / filename
    
    # Write packet
    output_path.write_text(yaml.dump(packet, sort_keys=False, allow_unicode=True), encoding="utf-8")
    
    # Update current pointer
    current_dir = PACKETS_BASE / "current" / slug
    current_dir.mkdir(parents=True, exist_ok=True)
    pointer_name = f"{packet_type.replace('_PACKET', '')}.current.yaml"
    pointer_path = current_dir / pointer_name
    pointer_path.write_text(yaml.dump(packet, sort_keys=False, allow_unicode=True), encoding="utf-8")
    
    return output_path


def generate_architect_context(slug: str, component_name: str, mode: int) -> dict:
    """Generate ARCHITECT_CONTEXT_PACKET."""
    caps = CAPS["architect"]
    
    goal = extract_goal_from_state()
    goal = truncate_text(goal, caps["goal_summary"])
    
    # Find recent work
    recent_refs = []
    last_packet = find_last_review_packet(slug)
    if last_packet:
        recent_refs.append({
            "path": str(last_packet.relative_to(REPO_ROOT)),
            "summary": "Last review packet for this workstream"
        })
    
    # Required templates
    required_templates = [
        {"path": "docs/02_protocols/Build_Handoff_Protocol_v1.0.md"},
        {"path": "docs/02_protocols/lifeos_packet_schemas_v1.yaml"},
    ]
    
    packet = {
        "packet_type": "ARCHITECT_CONTEXT_PACKET",
        "packet_id": generate_packet_id(),
        "component_human_name": component_name,
        "workstream_slug": slug,
        "created_at": now_iso(),
        "mode": mode,
        "context_ttl_hours": DEFAULT_TTL_HOURS,
        "goal_summary": goal,
        "constraints": truncate_list(["Follow existing protocol patterns", "No new external dependencies"], caps["constraints"]),
        "success_criteria": truncate_list(["Implementation complete", "Tests pass", "Documentation updated"], caps["success_criteria"]),
        "state_ref": "docs/11_admin/LIFEOS_STATE.md",
        "recent_work_refs": truncate_list(recent_refs, caps["refs"]),
        "required_templates_refs": truncate_list(required_templates, caps["refs"]),
        "council_trigger_policy_ref": "docs/02_protocols/Build_Handoff_Protocol_v1.0.md",
        "caps": caps,
    }
    return packet


def generate_builder_context(slug: str, component_name: str, mode: int) -> dict:
    """Generate BUILDER_CONTEXT_PACKET."""
    caps = CAPS["builder"]
    
    # Check for existing architect context
    architect_current = PACKETS_BASE / "current" / slug / "ARCHITECT_CONTEXT.current.yaml"
    architect_ref = normalize_repo_path(architect_current.relative_to(REPO_ROOT)) if architect_current.exists() else None
    
    # Check for readiness
    readiness_current = PACKETS_BASE / "current" / slug / "READINESS.current.yaml"
    readiness_ref = normalize_repo_path(readiness_current.relative_to(REPO_ROOT)) if readiness_current.exists() else None
    
    # Last review packet
    last_review = find_last_review_packet(slug)
    review_ref = normalize_repo_path(last_review.relative_to(REPO_ROOT)) if last_review else None
    
    packet = {
        "packet_type": "BUILDER_CONTEXT_PACKET",
        "packet_id": generate_packet_id(),
        "component_human_name": component_name,
        "workstream_slug": slug,
        "created_at": now_iso(),
        "context_ttl_hours": DEFAULT_TTL_HOURS,
        "state_ref": "docs/11_admin/LIFEOS_STATE.md",
        "architect_context_ref": architect_ref,
        "readiness_ref": readiness_ref,
        "last_review_packet_ref": review_ref,
        "constraints_summary": truncate_list([
            "Follow Build Handoff Protocol v1.0",
            "Emit Review Packet on completion",
            "Run preflight before implementation",
        ], caps["constraints"]),
        "success_criteria": truncate_list([
            "Tests pass",
            "Review Packet created",
        ], caps["success_criteria"]),
        "caps": caps,
    }
    return packet


def generate_council_context(slug: str, component_name: str, artefact_path: Optional[str]) -> dict:
    """Generate COUNCIL_REVIEW_PACKET with authoritative governance refs."""
    caps = CAPS["council"]
    
    # Determine artefact under review
    if artefact_path:
        artefact_ref = normalize_repo_path(artefact_path)
    else:
        last_review = find_last_review_packet(slug)
        artefact_ref = normalize_repo_path(last_review.relative_to(REPO_ROOT)) if last_review else "UNKNOWN"
    
    # Trigger reasons - CT-2 for governance paths, CT-3 explicitly decided
    # Per Build_Handoff_Protocol_v1.0.md Section 5:
    # CT-3 = "New CI script or gating change"
    # check_readiness.py IS a gating script (preflight enforcement)
    trigger_reasons = [
        {"trigger_id": "CT-2", "description": "Touches governance-protected paths (GEMINI.md, Protocol docs)"},
        {"trigger_id": "CT-3", "description": "New gating script (check_readiness.py enforces preflight)"},
    ]
    
    # Decision questions (capped)
    decision_questions = truncate_list([
        "Approve Article XVII as written?",
        "Approve Build_Handoff_Protocol_v1.0 as controlling protocol?",
        "Confirm trigger classification (CT-2/CT-3) is correct?",
        "Approve deferral posture (scripts implemented, pytest fallback acceptable)?",
        "Any mandatory amendments before activation?",
    ], caps["decision_questions"])
    
    # Canonical governance refs (deterministic, capped)
    role_prompts = truncate_list(discover_council_role_prompts(), caps["refs"])
    procedure_refs = truncate_list(discover_council_procedure_refs(), caps["refs"])
    
    packet = {
        "packet_type": "COUNCIL_REVIEW_PACKET",
        "packet_id": generate_packet_id(),
        "component_human_name": component_name,
        "workstream_slug": slug,
        "created_at": now_iso(),
        "artefact_under_review_ref": artefact_ref,
        "state_ref": "docs/11_admin/LIFEOS_STATE.md",
        "trigger_reasons": trigger_reasons,
        "scope_boundaries": {
            "paths_touched": [
                "GEMINI.md",
                "docs/02_protocols/Build_Handoff_Protocol_v1.0.md",
                "docs/11_admin/LIFEOS_STATE.md",
                "artifacts/workstreams.yaml",
            ],
            "protected_paths_policy_ref": PROTECTED_PATHS_POLICY_REF,
        },
        "required_decision_questions": decision_questions,
        "required_role_prompts_refs": role_prompts,
        "council_procedure_refs": procedure_refs,
    }
    return packet


def handle_resume(component_name: str, allow_provisional: bool = False) -> int:
    """Resume by restoring prior context to current pointer."""
    slug = resolve_component_to_slug(component_name, allow_provisional)
    if not slug:
        return 1
    
    # Find most recent versioned context
    for ctx_type in ["architect_context", "builder_context"]:
        ctx_dir = PACKETS_BASE / ctx_type
        if not ctx_dir.exists():
            continue
        
        matches = sorted(
            [p for p in ctx_dir.glob(f"*_{slug}_*.yaml")],
            key=lambda x: x.stat().st_mtime,
            reverse=True
        )
        if matches:
            # Copy to current
            current_dir = PACKETS_BASE / "current" / slug
            current_dir.mkdir(parents=True, exist_ok=True)
            pointer_name = f"{ctx_type.upper().replace('_CONTEXT', '_CONTEXT')}.current.yaml"
            pointer_path = current_dir / pointer_name
            pointer_path.write_text(matches[0].read_text(encoding="utf-8"), encoding="utf-8")
            print(f"Resumed: {matches[0]} -> {pointer_path}")
    
    print(f"Load: artifacts/packets/current/{slug}/")
    return 0


def main():
    parser = argparse.ArgumentParser(description="Generate context packs for agent roles")
    parser.add_argument("--for", dest="role", choices=["architect", "council", "builder"],
                        help="Target role for context pack")
    parser.add_argument("--component", help="Human-readable component name")
    parser.add_argument("--mode", type=int, default=0, choices=[0, 1, 2],
                        help="Operating mode (0=human-mediated, 1=semi-auto, 2=full-auto)")
    parser.add_argument("--artefact", help="Path to artefact for council review")
    parser.add_argument("--resume", action="store_true", help="Resume prior context")
    parser.add_argument("--allow-provisional", action="store_true",
                        help="Allow auto-adding unknown components as PROVISIONAL")
    
    args = parser.parse_args()
    
    # Handle resume
    if args.resume:
        if not args.component:
            print("Error: --resume requires --component", file=sys.stderr)
            return 1
        return handle_resume(args.component, args.allow_provisional)
    
    # Validate required args
    if not args.role:
        print("Error: --for is required", file=sys.stderr)
        return 1
    
    if not args.component and not args.artefact:
        print("Error: --component or --artefact required", file=sys.stderr)
        return 1
    
    # Resolve component
    component_name = args.component or "Unknown"
    slug = resolve_component_to_slug(component_name, args.allow_provisional)
    if not slug:
        return 1  # Blocked/Ambiguity
    
    # Generate packet
    if args.role == "architect":
        packet = generate_architect_context(slug, component_name, args.mode)
        packet_type = "ARCHITECT_CONTEXT_PACKET"
    elif args.role == "builder":
        packet = generate_builder_context(slug, component_name, args.mode)
        packet_type = "BUILDER_CONTEXT_PACKET"
    elif args.role == "council":
        packet = generate_council_context(slug, component_name, args.artefact)
        packet_type = "COUNCIL_REVIEW_PACKET"
    else:
        print(f"Error: Unknown role {args.role}", file=sys.stderr)
        return 1
    
    # Write packet
    output_path = write_packet(packet, packet_type, slug)
    print(f"Generated: {output_path}")
    print(f"Load: artifacts/packets/current/{slug}/{packet_type.replace('_PACKET', '')}.current.yaml")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
