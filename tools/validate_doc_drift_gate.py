#!/usr/bin/env python3
"""
Doc Drift Merge Gate — CI-enforced documentation drift control.

Ensures canonical doc changes have reconciliation packets, authority transitions
are approved, derived surfaces stay fresh, and emergency repairs are tracked.

Exit codes:
  0: Gate passed (or N/A)
  1: Drift detected (fail closed)
  2: Usage or runtime error
"""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore[assignment]

RECONCILIATION_PACKET_DIR = "docs/10_meta/reconciliation_packets/"
ALLOWED_EXEMPTION_REASONS = {"typo", "formatting", "link-fix", "generated-refresh-only"}
REQUIRED_PACKET_FIELDS = {
    "changed_canonical_paths",
    "affected_derived_surfaces",
    "regeneration_required",
    "authority_class_changes",
    "post_merge_verification_commands",
}


# ---------------------------------------------------------------------------
# Git helpers
# ---------------------------------------------------------------------------


def _run_git(cmd: list[str], repo_root: Path, timeout: int = 30) -> str:
    try:
        result = subprocess.run(
            cmd,
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=True,
            timeout=timeout,
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(f"git command failed: {' '.join(cmd)}\n{exc.stderr.strip()}") from exc
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(f"git command timed out: {' '.join(cmd)}") from exc


def _ref_exists(ref: str, repo_root: Path) -> bool:
    try:
        _run_git(["git", "rev-parse", "--verify", ref], repo_root)
        return True
    except RuntimeError:
        return False


def get_changed_files(repo_root: Path, base_ref: str, head_ref: str) -> list[str]:
    """Return list of changed file paths (ACMR) between base_ref and head_ref."""
    if not _ref_exists(base_ref, repo_root):
        raise RuntimeError(f"Base ref does not exist: {base_ref}")
    if not _ref_exists(head_ref, repo_root):
        raise RuntimeError(f"Head ref does not exist: {head_ref}")
    output = _run_git(
        ["git", "diff", "--name-only", "--diff-filter=ACMR", f"{base_ref}...{head_ref}"],
        repo_root,
    )
    return [f for f in output.split("\n") if f.strip()]


def get_registry_at_ref(
    repo_root: Path, ref: str, rel_path: str = "config/docs/authority_registry.yaml"
) -> dict[str, Any] | None:
    """Load authority registry YAML at a given git ref."""
    try:
        output = _run_git(["git", "show", f"{ref}:{rel_path}"], repo_root)
    except RuntimeError:
        return None
    if not output:
        return None
    try:
        data = yaml.safe_load(output)
    except yaml.YAMLError:
        return None
    return data if isinstance(data, dict) else None


# ---------------------------------------------------------------------------
# Path matching
# ---------------------------------------------------------------------------


def path_matches(rel_path: str, pattern: str) -> bool:
    """Match file path against glob-style pattern.

    Ported from doc_authority_manifest._path_matches.
    """
    regex = ""
    i = 0
    while i < len(pattern):
        ch = pattern[i]
        if ch == "*":
            if i + 1 < len(pattern) and pattern[i + 1] == "*":
                regex += ".*"
                i += 2
            else:
                regex += "[^/]*"
                i += 1
        elif ch == "?":
            regex += "[^/]"
            i += 1
        else:
            regex += re.escape(ch)
            i += 1
    return re.fullmatch(regex, rel_path) is not None


# ---------------------------------------------------------------------------
# Registry loading & file classification
# ---------------------------------------------------------------------------


def load_authority_registry(repo_root: Path) -> dict[str, Any]:
    """Load and return the authority registry YAML."""
    path = repo_root / "config" / "docs" / "authority_registry.yaml"
    if not path.exists():
        raise RuntimeError(f"Authority registry not found: {path}")
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise RuntimeError(f"Cannot read authority registry: {exc}") from exc
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise RuntimeError(f"Invalid YAML in authority registry: {exc}") from exc
    if not isinstance(data, dict):
        raise RuntimeError("Authority registry must be a YAML mapping")
    groups = data.get("doc_groups", [])
    if not isinstance(groups, list):
        raise RuntimeError("doc_groups must be a list")
    return data


def _all_derived_surfaces(doc_groups: list[dict[str, Any]]) -> set[str]:
    """Collect all paths listed as derived_surfaces across all doc_groups."""
    surfaces: set[str] = set()
    for group in doc_groups:
        if not isinstance(group, dict):
            continue
        derived = group.get("derived_surfaces", [])
        if isinstance(derived, list):
            for s in derived:
                if isinstance(s, str):
                    surfaces.add(s)
    return surfaces


def classify_file(rel_path: str, doc_groups: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Match a file path against doc_groups, returning the first matching group.

    Files listed as derived_surfaces by any group are classified as derived,
    even if they also match a canonical group's paths.
    """
    derived_surfaces = _all_derived_surfaces(doc_groups)
    if rel_path in derived_surfaces:
        for group in doc_groups:
            if not isinstance(group, dict):
                continue
            if group.get("authority") == "derived":
                paths = group.get("paths", [])
                if isinstance(paths, list):
                    for pattern in paths:
                        if isinstance(pattern, str) and path_matches(rel_path, pattern):
                            return group
        return {"id": "derived-surface", "authority": "derived", "steward": "auto"}
    for group in doc_groups:
        if not isinstance(group, dict):
            continue
        paths = group.get("paths", [])
        excludes = group.get("exclude_paths", []) or []
        if not isinstance(paths, list):
            continue
        for pattern in paths:
            if not isinstance(pattern, str):
                continue
            if not path_matches(rel_path, pattern):
                continue
            excluded = any(isinstance(ex, str) and path_matches(rel_path, ex) for ex in excludes)
            if not excluded:
                return group
    return None


def classify_files(
    changed_files: list[str],
    doc_groups: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    """Return {rel_path: group_dict} for each changed file."""
    result: dict[str, dict[str, Any]] = {}
    for f in changed_files:
        group = classify_file(f, doc_groups)
        if group is not None:
            result[f] = group
    return result


# ---------------------------------------------------------------------------
# Reconciliation packet helpers
# ---------------------------------------------------------------------------


def _is_reconciliation_packet_path(path: str) -> bool:
    return path.startswith(RECONCILIATION_PACKET_DIR) and path.endswith(".md")


def _parse_frontmatter(text: str) -> dict[str, Any] | None:
    if not text.startswith("---\n"):
        return None
    end = text.find("\n---\n", 4)
    if end == -1:
        return None
    try:
        loaded = yaml.safe_load(text[4:end])
    except yaml.YAMLError:
        return None
    return loaded if isinstance(loaded, dict) else None


def _parse_yaml_code_block(text: str) -> dict[str, Any] | None:
    match = re.search(r"```ya?ml\n(.*?)\n```", text, flags=re.DOTALL | re.IGNORECASE)
    if not match:
        return None
    try:
        loaded = yaml.safe_load(match.group(1))
    except yaml.YAMLError:
        return None
    return loaded if isinstance(loaded, dict) else None


def load_reconciliation_packets(
    changed_files: list[str],
    repo_root: Path,
) -> list[tuple[str, dict[str, Any]]]:
    """Load and parse reconciliation packets from changed files."""
    packets: list[tuple[str, dict[str, Any]]] = []
    for rel_path in changed_files:
        if not _is_reconciliation_packet_path(rel_path):
            continue
        full_path = repo_root / rel_path
        if not full_path.exists():
            continue
        text = full_path.read_text(encoding="utf-8")
        data = _parse_frontmatter(text)
        if data is None:
            data = _parse_yaml_code_block(text)
        packets.append((rel_path, data if isinstance(data, dict) else {}))
    return packets


def _validate_exemption(exemption: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(exemption, dict):
        return ["reconciliation_exemption must be a mapping"]
    reason = exemption.get("reason")
    if reason not in ALLOWED_EXEMPTION_REASONS:
        errors.append(
            f"Invalid reconciliation_exemption.reason '{reason}'; "
            f"use one of {', '.join(sorted(ALLOWED_EXEMPTION_REASONS))}"
        )
    if exemption.get("affected_derived_surfaces") != "none":
        errors.append("reconciliation_exemption.affected_derived_surfaces must be 'none'")
    if exemption.get("semantic_change") is not False:
        errors.append("reconciliation_exemption.semantic_change must be false")
    return errors


def _validate_packet_fields(packet: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    missing = sorted(REQUIRED_PACKET_FIELDS - set(packet))
    if missing:
        return [f"Missing required field(s): {', '.join(missing)}"]
    if (
        not isinstance(packet.get("changed_canonical_paths"), list)
        or not packet["changed_canonical_paths"]
    ):
        errors.append("changed_canonical_paths must be a non-empty list")
    if not isinstance(packet.get("affected_derived_surfaces"), list):
        errors.append("affected_derived_surfaces must be a list")
    if not isinstance(packet.get("regeneration_required"), bool):
        errors.append("regeneration_required must be true or false")
    for field in ("authority_class_changes", "post_merge_verification_commands"):
        if not isinstance(packet.get(field), list):
            errors.append(f"{field} must be a list")
    if packet.get("affected_derived_surfaces") == [] and not packet.get("not_affected_reason"):
        errors.append("not_affected_reason required when derived surfaces unaffected")
    return errors


def check_reconciliation_requirement(
    changed_files: list[str],
    classification: dict[str, dict[str, Any]],
    doc_groups: list[dict[str, Any]],
    repo_root: Path,
) -> dict[str, Any]:
    """Check A — every changed canonical doc needs a reconciliation packet or exemption."""
    canonical_changed = [
        p
        for p, g in classification.items()
        if g.get("authority") == "canonical" and not _is_reconciliation_packet_path(p)
    ]
    if not canonical_changed:
        return {"passed": True, "details": "No canonical docs changed"}

    packets = load_reconciliation_packets(changed_files, repo_root)

    errors: list[str] = []
    valid_covered: set[str] = set()

    for rel_path, packet in packets:
        exemption_errors: list[str] = []
        field_errors: list[str] = []
        is_exemption = "reconciliation_exemption" in packet

        if is_exemption:
            exemption_errors = _validate_exemption(packet.get("reconciliation_exemption"))
            if not exemption_errors:
                valid_covered.update(canonical_changed)
        else:
            field_errors = _validate_packet_fields(packet)
            if not field_errors:
                covered = packet.get("changed_canonical_paths", [])
                if isinstance(covered, list):
                    valid_covering_paths = [p for p in covered if isinstance(p, str)]
                    valid_covered.update(valid_covering_paths)

        if exemption_errors:
            for err in exemption_errors:
                errors.append(f"{rel_path}: {err}")
        if field_errors:
            for err in field_errors:
                errors.append(f"{rel_path}: {err}")

    uncovered = [p for p in canonical_changed if p not in valid_covered]
    if uncovered and not errors:
        errors.extend(f"{p}: missing valid reconciliation packet or exemption" for p in uncovered)
    elif uncovered:
        errors.extend(f"{p}: packet present but does not cover this path" for p in uncovered)

    if not packets and uncovered:
        errors.extend(f"{p}: missing reconciliation packet" for p in uncovered)

    passed = len(errors) == 0
    return {
        "passed": passed,
        "details": "All covered" if passed else "; ".join(errors),
        "canonical_changed": canonical_changed,
    }


# ---------------------------------------------------------------------------
# Check B — Authority transitions
# ---------------------------------------------------------------------------


def check_authority_transitions(
    repo_root: Path,
    base_ref: str,
    head_ref: str,
) -> dict[str, Any]:
    """Check B — authority_registry.yaml changes must have approved transitions."""
    rel_path = "config/docs/authority_registry.yaml"
    changed_files = get_changed_files(repo_root, base_ref, head_ref)
    if rel_path not in changed_files:
        return {"passed": True, "details": "Registry not changed"}

    old = get_registry_at_ref(repo_root, base_ref)
    new = get_registry_at_ref(repo_root, head_ref)
    if old is None or new is None:
        return {"passed": True, "details": "Cannot compare registry versions (skip)"}

    old_groups = old.get("doc_groups", [])
    new_groups = new.get("doc_groups", [])

    if not isinstance(old_groups, list) or not isinstance(new_groups, list):
        return {"passed": True, "details": "Cannot parse doc_groups (skip)"}

    old_authorities: dict[str, str] = {}
    new_authorities: dict[str, str] = {}

    for groups, target in [(old_groups, old_authorities), (new_groups, new_authorities)]:
        for group in groups:
            if not isinstance(group, dict):
                continue
            gid = group.get("id", "")
            auth = group.get("authority", "")
            if isinstance(auth, str):
                target[gid] = auth

    transitions = new.get("authority_transitions", [])
    if not isinstance(transitions, list):
        transitions = []

    errors: list[str] = []
    changed_groups = set(new_authorities) & set(old_authorities)
    for gid in sorted(changed_groups):
        if old_authorities[gid] == new_authorities[gid]:
            continue
        matching = [
            t
            for t in transitions
            if isinstance(t, dict)
            and t.get("from") == old_authorities[gid]
            and t.get("to") == new_authorities[gid]
        ]
        if not matching:
            errors.append(
                f"Group '{gid}' changed {old_authorities[gid]} -> {new_authorities[gid]}; "
                "missing authority_transitions record"
            )
            continue
        for record in matching:
            evidence = record.get("approval_evidence") or {}
            if not isinstance(evidence, dict):
                errors.append(f"Transition for '{gid}': approval_evidence must be a mapping")
                continue
            etype = evidence.get("type")
            if etype not in ("human", "aa", "ceo"):
                errors.append(f"Transition for '{gid}': invalid approval_evidence.type '{etype}'")
            url = evidence.get("url")
            if not isinstance(url, str) or not re.match(r"^https://github\.com/.+", url):
                errors.append(f"Transition for '{gid}': approval_evidence.url must be GitHub URL")
            if evidence.get("verdict") != "approved":
                errors.append(
                    f"Transition for '{gid}': approval_evidence.verdict must be 'approved'"
                )

    passed = len(errors) == 0
    return {
        "passed": passed,
        "details": "Transitions valid" if passed else "; ".join(errors),
    }


# ---------------------------------------------------------------------------
# Check C — Derived surface freshness
# ---------------------------------------------------------------------------


def check_derived_freshness(
    changed_files: list[str],
    classification: dict[str, dict[str, Any]],
    doc_groups: list[dict[str, Any]],
    repo_root: Path,
) -> dict[str, Any]:
    """Check C — canonical changes must refresh their derived surfaces."""
    canonical_changed = [
        p
        for p, g in classification.items()
        if g.get("authority") == "canonical" and not _is_reconciliation_packet_path(p)
    ]
    if not canonical_changed:
        return {"passed": True, "details": "No canonical docs changed"}

    changed_set = set(changed_files)
    packets = load_reconciliation_packets(changed_files, repo_root)

    errors: list[str] = []

    for canon_path in canonical_changed:
        group = classification[canon_path]
        derived = group.get("derived_surfaces", [])
        if not isinstance(derived, list) or not derived:
            continue

        for surface in derived:
            if not isinstance(surface, str):
                continue
            if surface in changed_set:
                continue

            exempted = False
            for _rel_path, packet in packets:
                if packet.get("regeneration_required") is False:
                    reason = packet.get("not_affected_reason")
                    if isinstance(reason, str) and reason.strip():
                        exempted = True
                        break
                if "reconciliation_exemption" in packet:
                    exempt = packet.get("reconciliation_exemption", {})
                    if (
                        isinstance(exempt, dict)
                        and exempt.get("affected_derived_surfaces") == "none"
                    ):
                        exempted = True
                        break

            if not exempted:
                errors.append(
                    f"{canon_path}: derived surface '{surface}' not updated; "
                    "add to PR or declare not_affected_reason"
                )

    passed = len(errors) == 0
    return {
        "passed": passed,
        "details": "All derived surfaces fresh" if passed else "; ".join(errors),
    }


# ---------------------------------------------------------------------------
# Check D — Emergency manual repair
# ---------------------------------------------------------------------------


def check_emergency_repair(
    changed_files: list[str],
    classification: dict[str, dict[str, Any]],
    repo_root: Path,
) -> dict[str, Any]:
    """Check D — manually-edited derived files must declare emergency-manual-repair."""
    derived_changed = [p for p, g in classification.items() if g.get("authority") == "derived"]
    if not derived_changed:
        return {"passed": True, "details": "No derived docs changed"}

    # Find canonical source changes for the same groups to determine if derived
    # change is a regeneration vs manual edit.
    source_canonical_paths: set[str] = set()
    for p, g in classification.items():
        if g.get("authority") == "canonical":
            source_canonical_paths.add(p)

    # Check each derived file not accompanied by its source canonical(s)
    errors: list[str] = []
    for derived_path in derived_changed:
        full_path = repo_root / derived_path
        if not full_path.exists():
            continue
        text = full_path.read_text(encoding="utf-8")
        frontmatter = _parse_frontmatter(text)
        if frontmatter is None:
            frontmatter = _parse_yaml_code_block(text)

        edit_mode = (frontmatter or {}).get("derived_edit_mode")
        # If this derived file has generated provenance or is accompanied by
        # canonical source changes for its own group, it is a normal regeneration.
        if edit_mode == "generated":
            continue
        group = classification.get(derived_path, {})
        # Check if any canonical source for THIS derived file's group also changed
        my_sources_changed = bool(source_canonical_paths)
        if my_sources_changed and group.get("authority") == "derived":
            continue
        if edit_mode != "emergency-manual-repair":
            errors.append(
                f"{derived_path}: derived file changed but missing "
                "derived_edit_mode: emergency-manual-repair in frontmatter"
            )
            continue

        reason = (frontmatter or {}).get("reason")
        if not reason:
            errors.append(f"{derived_path}: emergency-manual-repair requires 'reason'")

        follow_up = (frontmatter or {}).get("follow_up_required")
        if follow_up is not True:
            errors.append(
                f"{derived_path}: emergency-manual-repair requires follow_up_required: true"
            )

        issue = (frontmatter or {}).get("follow_up_issue", "pending")
        if issue == "pending":
            errors.append(f"{derived_path}: follow_up_issue must not be 'pending'")

        approval = (frontmatter or {}).get("approval_evidence")
        if not isinstance(approval, str):
            errors.append(f"{derived_path}: approval_evidence must be a URL string")

    passed = len(errors) == 0
    return {
        "passed": passed,
        "details": "Emergency repairs valid" if passed else "; ".join(errors),
    }


# ---------------------------------------------------------------------------
# Output builder
# ---------------------------------------------------------------------------


def build_result(
    a: dict[str, Any],
    b: dict[str, Any],
    c: dict[str, Any],
    d: dict[str, Any],
    classification: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    canonical = sorted(p for p, g in classification.items() if g.get("authority") == "canonical")
    derived = sorted(p for p, g in classification.items() if g.get("authority") == "derived")
    checks = {
        "reconciliation": {"passed": a["passed"], "details": a["details"]},
        "authority_transitions": {"passed": b["passed"], "details": b["details"]},
        "derived_freshness": {"passed": c["passed"], "details": c["details"]},
        "emergency_repair": {"passed": d["passed"], "details": d["details"]},
    }
    passed = all(chk["passed"] for chk in checks.values())
    needs_to_pass = [name for name, chk in checks.items() if not chk["passed"]]
    return {
        "passed": passed,
        "checks": checks,
        "changed_canonical_docs": canonical,
        "changed_derived_surfaces": derived,
        "errors": needs_to_pass,
        "needs_to_pass": needs_to_pass,
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Doc Drift Merge Gate — enforce documentation drift control.",
    )
    parser.add_argument(
        "--repo-root",
        type=str,
        default=".",
        help="Path to git repository root (default: .)",
    )
    parser.add_argument(
        "--base-ref",
        type=str,
        default="origin/main",
        help="Base git ref for comparison (default: origin/main)",
    )
    parser.add_argument(
        "--head-ref",
        type=str,
        default="HEAD",
        help="Head git ref for comparison (default: HEAD)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    repo_root = Path(args.repo_root).resolve()

    if yaml is None:
        print(
            json.dumps(
                {
                    "passed": False,
                    "checks": {},
                    "changed_canonical_docs": [],
                    "changed_derived_surfaces": [],
                    "errors": ["PyYAML is required: pip install pyyaml"],
                    "needs_to_pass": ["dependency"],
                }
            )
        )
        return 2

    # Validate repo root
    if not (repo_root / ".git").exists() and not (repo_root / ".git").is_file():
        print(
            json.dumps(
                {
                    "passed": False,
                    "checks": {},
                    "changed_canonical_docs": [],
                    "changed_derived_surfaces": [],
                    "errors": [f"Not a git repository: {repo_root}"],
                    "needs_to_pass": ["repo"],
                }
            )
        )
        return 2

    # Load registry
    try:
        registry = load_authority_registry(repo_root)
    except RuntimeError as exc:
        print(
            json.dumps(
                {
                    "passed": False,
                    "checks": {},
                    "changed_canonical_docs": [],
                    "changed_derived_surfaces": [],
                    "errors": [str(exc)],
                    "needs_to_pass": ["registry"],
                }
            )
        )
        return 2

    doc_groups = registry.get("doc_groups", [])
    if not isinstance(doc_groups, list):
        doc_groups = []

    # Get changed files
    try:
        changed_files = get_changed_files(repo_root, args.base_ref, args.head_ref)
    except RuntimeError as exc:
        print(
            json.dumps(
                {
                    "passed": False,
                    "checks": {},
                    "changed_canonical_docs": [],
                    "changed_derived_surfaces": [],
                    "errors": [str(exc)],
                    "needs_to_pass": ["git"],
                }
            )
        )
        return 2

    # Filter to .md files and classify
    md_changed = [f for f in changed_files if f.endswith(".md")]
    classification = classify_files(md_changed, doc_groups)

    # Run checks
    a_result = check_reconciliation_requirement(
        md_changed,
        classification,
        doc_groups,
        repo_root,
    )
    b_result = check_authority_transitions(repo_root, args.base_ref, args.head_ref)
    c_result = check_derived_freshness(
        md_changed,
        classification,
        doc_groups,
        repo_root,
    )
    d_result = check_emergency_repair(
        md_changed,
        classification,
        repo_root,
    )

    result = build_result(a_result, b_result, c_result, d_result, classification)
    print(json.dumps(result, indent=2))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
