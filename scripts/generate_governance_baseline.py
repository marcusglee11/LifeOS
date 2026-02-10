#!/usr/bin/env python3
"""
Governance Baseline Generator

Generates config/governance_baseline.yaml with SHA-256 hashes of all
governance surfaces per LifeOS_Autonomous_Build_Loop_Architecture_v0.3.md.

Usage:
    python scripts/generate_governance_baseline.py           # Preview only
    python scripts/generate_governance_baseline.py --write   # Write to file

This script is deterministic:
- Surfaces are enumerated in canonical order
- SHA-256 hashes are computed identically on all platforms
- YAML output uses sorted keys
"""

from __future__ import annotations

import argparse
import hashlib
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import List

import yaml


# Governance surfaces per Architecture v0.3 section 2.3
# These are the authoritative paths that must be protected
GOVERNANCE_SURFACES = [
    # Agent constitutions
    "CLAUDE.md",
    "GEMINI.md",
    # Model mapping
    "config/models.yaml",
    # NOTE: config/governance_baseline.yaml is NOT included here to avoid self-reference
    # The baseline is the integrity manifest itself, not a governed artifact
    # Its integrity is ensured by git commit + CEO approval
    # Agent role prompts (glob pattern expanded below)
    "config/agent_roles",
    # Envelope policy
    "scripts/opencode_gate_policy.py",
    # Packet transforms
    "runtime/orchestration/transforms",
    # Self-modification protection (the protector file)
    "runtime/governance/self_mod_protection.py",
    # Architecture documents (glob pattern expanded below)
    "docs/03_runtime/LifeOS_Autonomous_Build_Loop_Architecture",
    # Protected doc roots
    "docs/00_foundations",
    "docs/01_governance",
]


def compute_file_hash(file_path: Path) -> str:
    """Compute SHA-256 hash of file contents."""
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def enumerate_surfaces(repo_root: Path) -> List[dict]:
    """
    Enumerate all governance surfaces and compute their hashes.

    Returns list of dicts with 'path' and 'sha256' keys, sorted by path.
    """
    artifacts = []

    for surface in GOVERNANCE_SURFACES:
        surface_path = repo_root / surface

        if surface_path.is_file():
            # Direct file reference
            artifacts.append({
                "path": surface,
                "sha256": compute_file_hash(surface_path),
            })
        elif surface_path.is_dir():
            # Directory: enumerate all files recursively
            for file_path in sorted(surface_path.rglob("*")):
                if file_path.is_file():
                    rel_path = str(file_path.relative_to(repo_root)).replace("\\", "/")
                    artifacts.append({
                        "path": rel_path,
                        "sha256": compute_file_hash(file_path),
                    })
        else:
            # Pattern match (prefix)
            parent = surface_path.parent
            prefix = surface_path.name
            if parent.exists():
                for file_path in sorted(parent.glob(f"{prefix}*")):
                    if file_path.is_file():
                        rel_path = str(file_path.relative_to(repo_root)).replace("\\", "/")
                        artifacts.append({
                            "path": rel_path,
                            "sha256": compute_file_hash(file_path),
                        })

    # Sort by path for determinism
    return sorted(artifacts, key=lambda x: x["path"])


def generate_baseline(repo_root: Path, council_ruling_ref: str = None) -> dict:
    """
    Generate the complete baseline manifest.

    Args:
        repo_root: Repository root path
        council_ruling_ref: Optional reference to Council ruling authorizing this baseline

    Returns:
        Dict suitable for YAML serialization
    """
    artifacts = enumerate_surfaces(repo_root)

    manifest = {
        "baseline_version": "1.0",
        # NOTE: No generated_at timestamp - git commit history provides this
        # Timestamps create unnecessary churn and prevent baseline convergence
        "approved_by": "CEO",  # Per spec, CEO authorizes baseline
        "council_ruling_ref": council_ruling_ref,
        "hash_algorithm": "SHA-256",
        "path_normalization": "relpath_from_repo_root",
        "artifacts": artifacts,
    }

    return manifest


def main():
    parser = argparse.ArgumentParser(
        description="Generate governance baseline manifest"
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="Write baseline to config/governance_baseline.yaml (default: preview only)"
    )
    parser.add_argument(
        "--council-ruling",
        type=str,
        default=None,
        help="Reference to Council ruling authorizing this baseline"
    )
    parser.add_argument(
        "--repo-root",
        type=str,
        default=None,
        help="Repository root (default: auto-detect)"
    )

    args = parser.parse_args()

    # Detect repo root
    if args.repo_root:
        repo_root = Path(args.repo_root)
    else:
        # Walk up from script location to find .git
        script_dir = Path(__file__).parent
        repo_root = script_dir.parent
        if not (repo_root / ".git").exists():
            print("ERROR: Could not detect repo root. Use --repo-root.", file=sys.stderr)
            sys.exit(1)

    print(f"Repository root: {repo_root}")
    print()

    # Generate baseline
    manifest = generate_baseline(repo_root, args.council_ruling)

    # YAML output with deterministic ordering
    yaml_output = yaml.dump(
        manifest,
        default_flow_style=False,
        sort_keys=True,
        allow_unicode=True,
    )

    if args.write:
        output_path = repo_root / "config" / "governance_baseline.yaml"
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(yaml_output)

        print(f"Baseline written to: {output_path}")
        print(f"Artifacts enumerated: {len(manifest['artifacts'])}")
        print()
        print("IMPORTANT: This baseline must be reviewed and approved by CEO.")
        print("To verify: python -c \"from runtime.governance.baseline_checker import verify_governance_baseline; verify_governance_baseline()\"")
    else:
        print("=== PREVIEW (use --write to persist) ===")
        print()
        print(yaml_output)
        print()
        print(f"Total artifacts: {len(manifest['artifacts'])}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
