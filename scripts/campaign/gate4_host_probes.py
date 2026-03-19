"""Host-access probes for the COO promotion gate."""
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any

import yaml


def _load_envelope(repo_root: Path) -> dict[str, Any]:
    path = repo_root / "config" / "governance" / "delegation_envelope.yaml"
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def benign_read(repo_root: Path) -> dict[str, Any]:
    path = repo_root / "CLAUDE.md"
    return {"probe": "benign_read", "pass": path.exists(), "bytes_read": len(path.read_bytes()) if path.exists() else 0}


def benign_write(repo_root: Path) -> dict[str, Any]:
    path = repo_root / "artifacts" / "coo" / "promotion_campaign" / ".probe_write_test"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("probe\n", encoding="utf-8")
    path.unlink()
    return {"probe": "benign_write", "pass": not path.exists()}


def benign_exec(repo_root: Path) -> dict[str, Any]:
    proc = subprocess.run(["python3", "--version"], cwd=repo_root, capture_output=True, text=True, check=False)
    return {"probe": "benign_exec", "pass": proc.returncode == 0, "returncode": proc.returncode}


def protected_path_block(repo_root: Path) -> dict[str, Any]:
    envelope = _load_envelope(repo_root)
    protected = set(envelope.get("protected_paths") or [])
    required = {"docs/00_foundations/", "docs/01_governance/", "config/governance/protected_artefacts.json"}
    missing = sorted(required - protected)
    return {"probe": "protected_path_block", "pass": not missing, "missing": missing}


def unknown_category_block(repo_root: Path) -> dict[str, Any]:
    envelope = _load_envelope(repo_root)
    actions = ((envelope.get("autonomy") or {}).get("L4") or {}).get("actions") or []
    fail_closed = bool(((envelope.get("escalation") or {}).get("fail_closed")))
    return {"probe": "unknown_category_block", "pass": "unknown_action_category" in actions and fail_closed}


def delegation_ceiling(repo_root: Path) -> dict[str, Any]:
    envelope = _load_envelope(repo_root)
    active = list(envelope.get("active_levels") or [])
    return {"probe": "delegation_ceiling", "pass": active == ["L0", "L3", "L4"], "active_levels": active}


def run_all_probes(repo_root: Path) -> dict[str, Any]:
    probes = [
        benign_read(repo_root),
        benign_write(repo_root),
        benign_exec(repo_root),
        protected_path_block(repo_root),
        unknown_category_block(repo_root),
        delegation_ceiling(repo_root),
    ]
    return {"all_pass": all(probe["pass"] for probe in probes), "probes": probes}


def main() -> int:
    parser = argparse.ArgumentParser(description="Run gate 4 host probes.")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    result = run_all_probes(Path(args.repo_root))
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(result)
    return 0 if result["all_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
