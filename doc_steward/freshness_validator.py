"""
Doc freshness validator with mode-gated enforcement.

Implements Doc_Freshness_Gate_Spec_v1.0.md with structured contradiction detection.

Modes:
- off: No freshness checking
- warn: Emit warnings but do not fail
- block: Fail on violations

Mode is controlled by env var LIFEOS_DOC_FRESHNESS_MODE (default: off)
"""

import json
import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

ENTRYPOINT_REQUIRED_LINKS = (
    "docs/INDEX.md",
    "docs/08_manuals/LifeOS_Operator_Onboarding.md",
    "docs/11_admin/LIFEOS_STATE.md",
    "docs/00_foundations/LifeOS Target Architecture v2.3c.md",
)


def get_freshness_mode() -> str:
    """Get freshness mode from environment."""
    mode = os.environ.get("LIFEOS_DOC_FRESHNESS_MODE", "off")
    if mode not in {"off", "warn", "block"}:
        # Invalid mode, default to off
        return "off"
    return mode


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _normalize_markdown_link_target(target: str) -> str:
    return target.replace("%20", " ").strip("./")


def _markdown_links(text: str) -> set[str]:
    links = set()
    for target in re.findall(r"\[[^\]]+\]\(([^)]+)\)", text):
        links.add(_normalize_markdown_link_target(target.split("#", 1)[0]))
    return links


def _authority_registry_declares(path: str, registry_text: str, authority: str) -> bool:
    """Return whether the YAML authority registry declares path with authority."""
    try:
        registry = yaml.safe_load(registry_text) or {}
    except yaml.YAMLError:
        return False
    if not isinstance(registry, dict):
        return False
    doc_groups = registry.get("doc_groups", [])
    if not isinstance(doc_groups, list):
        return False
    for group in doc_groups:
        if not isinstance(group, dict):
            continue
        paths = group.get("paths", [])
        if not isinstance(paths, list):
            continue
        if group.get("authority") == authority and path in paths:
            return True
    return False


def check_entrypoint_freshness(repo_root: str | Path) -> list[dict[str, object]]:
    """Detect low-noise README/operator entrypoint drift for maintenance sweeps.

    The check is read-only and issue-creator friendly: each finding contains stable
    fields suitable for a single deduped sweep issue. It does not decide semantic
    authority disputes or mutate docs.
    """
    repo_path = Path(repo_root).resolve()
    findings: list[dict[str, object]] = []

    readme_path = repo_path / "README.md"
    state_path = repo_path / "docs" / "11_admin" / "LIFEOS_STATE.md"
    registry_path = repo_path / "config" / "docs" / "authority_registry.yaml"

    required_paths = (readme_path, state_path, registry_path)
    missing = [str(p.relative_to(repo_path)) for p in required_paths if not p.exists()]
    if missing:
        findings.append(
            {
                "id": "entrypoint-required-file-missing",
                "severity": "warning",
                "paths": missing,
                "evidence": "Required entrypoint freshness input file is missing.",
                "recommended_recovery": (
                    "Restore the missing file before running README entrypoint drift checks."
                ),
                "authority_class": "canonical",
            }
        )
        return findings

    readme = _read_text(readme_path)
    state = _read_text(state_path)
    registry = _read_text(registry_path)
    links = _markdown_links(readme)

    missing_links = [target for target in ENTRYPOINT_REQUIRED_LINKS if target not in links]
    if missing_links:
        findings.append(
            {
                "id": "entrypoint-read-order-missing-links",
                "severity": "warning",
                "paths": ["README.md"],
                "evidence": f"README operator read-order is missing: {', '.join(missing_links)}",
                "recommended_recovery": "Add the missing canonical read-order links to README.md.",
                "authority_class": "canonical",
            }
        )

    stale_status_markers = (
        "Phase 4 Preparation",
        "Tier-3 Authorized",
        "Phase 4 — Tier-3",
    )
    if any(marker in readme for marker in stale_status_markers) and "COO Bootstrap" in state:
        findings.append(
            {
                "id": "entrypoint-readme-status-contradicts-lifeos-state",
                "severity": "warning",
                "paths": ["README.md", "docs/11_admin/LIFEOS_STATE.md"],
                "evidence": (
                    "README status still describes old Phase 4/Tier-3 state while "
                    "LIFEOS_STATE records later COO bootstrap/live COO state."
                ),
                "recommended_recovery": (
                    "Refresh README current-status wording from LIFEOS_STATE.md "
                    "before enabling freshness automation."
                ),
                "authority_class": "canonical",
            }
        )

    if "derived" not in readme.lower() or "Repo canon wins" not in readme:
        findings.append(
            {
                "id": "entrypoint-derived-surface-boundary-missing",
                "severity": "warning",
                "paths": ["README.md", "docs/LifeOS_Strategic_Corpus.md"],
                "evidence": (
                    "README does not clearly state that strategic corpus/wiki "
                    "surfaces are derived and repo canon wins on conflict."
                ),
                "recommended_recovery": (
                    "State the canonical-vs-derived conflict rule in README.md."
                ),
                "authority_class": "canonical/derived",
            }
        )

    if not _authority_registry_declares("docs/INDEX.md", registry, "canonical"):
        findings.append(
            {
                "id": "entrypoint-index-authority-registry-mismatch",
                "severity": "warning",
                "paths": ["config/docs/authority_registry.yaml", "docs/INDEX.md"],
                "evidence": (
                    "authority_registry.yaml does not declare docs/INDEX.md "
                    "as canonical root navigation."
                ),
                "recommended_recovery": (
                    "Reconcile docs/INDEX.md authority classification before "
                    "relying on README read-order checks."
                ),
                "authority_class": "canonical",
            }
        )

    if not _authority_registry_declares("docs/LifeOS_Strategic_Corpus.md", registry, "derived"):
        findings.append(
            {
                "id": "entrypoint-corpus-authority-registry-mismatch",
                "severity": "warning",
                "paths": ["config/docs/authority_registry.yaml", "docs/LifeOS_Strategic_Corpus.md"],
                "evidence": (
                    "authority_registry.yaml does not declare "
                    "docs/LifeOS_Strategic_Corpus.md as derived."
                ),
                "recommended_recovery": (
                    "Reconcile strategic corpus authority classification before "
                    "relying on README derived-surface checks."
                ),
                "authority_class": "derived",
            }
        )

    return findings


def check_freshness(repo_root: str) -> tuple[list[str], list[str]]:
    """
    Check doc freshness and contradictions.

    Args:
        repo_root: Path to repository root

    Returns:
        Tuple of (warnings, errors)
        - warnings: List of warning messages
        - errors: List of error messages (blocking in block mode)
    """
    mode = get_freshness_mode()

    if mode == "off":
        # Freshness checking disabled
        return ([], [])

    warnings: list[str] = []
    errors: list[str] = []

    repo_path = Path(repo_root).resolve()
    status_file = repo_path / "artifacts" / "status" / "runtime_status.json"

    # Check if status file exists
    if not status_file.exists():
        msg = f"Runtime status file missing: {status_file}"
        if mode == "warn":
            warnings.append(msg)
        elif mode == "block":
            errors.append(msg)
        return (warnings, errors)

    # Check file age (24h SLA)
    try:
        file_mtime = datetime.fromtimestamp(status_file.stat().st_mtime, tz=timezone.utc)
        age = datetime.now(timezone.utc) - file_mtime
        sla_threshold = timedelta(hours=24)

        if age > sla_threshold:
            hours_stale = int(age.total_seconds() / 3600)
            msg = f"Runtime status file is stale: {status_file} (age: {hours_stale}h, SLA: 24h)"
            if mode == "warn":
                warnings.append(msg)
            elif mode == "block":
                errors.append(msg)
    except Exception as e:
        msg = f"Failed to check file age for {status_file}: {e}"
        if mode == "warn":
            warnings.append(msg)
        elif mode == "block":
            errors.append(msg)

    # Load and check structured contradictions
    try:
        with status_file.open("r", encoding="utf-8") as f:
            status_data = json.load(f)

        contradictions = status_data.get("contradictions", [])

        # Process contradictions
        for contradiction in contradictions:
            if not isinstance(contradiction, dict):
                continue

            contradiction_id = contradiction.get("id", "unknown")
            severity = contradiction.get("severity", "warn")
            message = contradiction.get("message", "No message provided")
            refs = contradiction.get("refs", [])

            refs_str = ", ".join(refs) if refs else "no references"
            full_msg = f"Contradiction [{contradiction_id}]: {message} (refs: {refs_str})"

            if severity == "block" and mode == "block":
                # Blocking contradiction in block mode
                errors.append(full_msg)
            else:
                # Warn severity, or block mode not active
                if mode in {"warn", "block"}:
                    warnings.append(full_msg)

    except json.JSONDecodeError as e:
        msg = f"Failed to parse runtime status JSON: {status_file}: {e}"
        if mode == "warn":
            warnings.append(msg)
        elif mode == "block":
            errors.append(msg)
    except Exception as e:
        msg = f"Failed to read runtime status file {status_file}: {e}"
        if mode == "warn":
            warnings.append(msg)
        elif mode == "block":
            errors.append(msg)

    return (warnings, errors)
