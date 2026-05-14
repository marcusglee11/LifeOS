"""Documentation authority manifest validator.

The central manifest is the machine authority for LifeOS documentation
classification. Optional per-file frontmatter is derivative and must agree with
this manifest.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Any, Iterable, Sequence

import yaml
from jsonschema import Draft202012Validator

ALLOWED_AUTHORITIES = {"canonical", "derived", "proposal-only", "deferred", "discarded"}
ALLOWED_APPROVAL_TYPES = {"human", "aa", "ceo"}
ALLOWED_RECONCILIATION_EXEMPTIONS = {
    "typo",
    "formatting",
    "link-fix",
    "generated-refresh-only",
}
RECONCILIATION_PACKET_PREFIX = "docs/10_meta/reconciliation_packets/"
RECONCILIATION_PACKET_REQUIRED_FIELDS = {
    "changed_canonical_paths",
    "affected_derived_surfaces",
    "regeneration_required",
    "authority_class_changes",
    "post_merge_verification_commands",
}
PROTECTED_TRANSITIONS = {
    ("proposal-only", "canonical"),
    ("deferred", "canonical"),
    ("canonical", "derived"),
    ("canonical", "proposal-only"),
    ("canonical", "deferred"),
    ("canonical", "discarded"),
}
DEFAULT_MANIFEST_PATH = Path("config/docs/authority_registry.yaml")
DOC_PATH_RE = re.compile(r"^docs/.+\.md$")
GITHUB_URL_RE = re.compile(r"^https://github\.com/[^/]+/[^/]+/(issues|pull)/\d+(#.*)?$")


class AuthorityManifestError(ValueError):
    """Raised when the manifest cannot be parsed as a mapping."""


def _unique_ordered(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        out.append(value)
    return out


def check_doc_authority_manifest(
    repo_root: str | Path,
    manifest_path: str | Path | None = None,
    previous_manifest_path: str | Path | None = None,
    changed_paths: Sequence[str] | None = None,
) -> list[str]:
    """Return validation errors for the documentation authority manifest."""
    root = Path(repo_root).resolve()
    rel_manifest = Path(manifest_path) if manifest_path else DEFAULT_MANIFEST_PATH
    manifest_file = rel_manifest if rel_manifest.is_absolute() else root / rel_manifest
    errors: list[str] = []

    if not manifest_file.exists():
        return [
            f"{_rel(manifest_file, root)}: missing documentation authority manifest; "
            f"create {DEFAULT_MANIFEST_PATH.as_posix()} and classify active docs."
        ]

    try:
        payload = yaml.safe_load(manifest_file.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        return [f"{_rel(manifest_file, root)}: invalid YAML: {exc}"]

    if not isinstance(payload, dict):
        return [f"{_rel(manifest_file, root)}: manifest must be a YAML mapping"]

    groups = payload.get("doc_groups", [])
    if not isinstance(groups, list):
        return [f"{_rel(manifest_file, root)}: doc_groups must be a list"]

    coverage, authorities = _manifest_path_authorities(payload, root, errors)
    errors.extend(_check_schema(payload, root, manifest_file))
    errors.extend(_check_derived_source_authority(payload, root, authorities))

    previous_payload = _load_previous_manifest_payload(root, rel_manifest, previous_manifest_path)
    if previous_payload is not None:
        previous_errors: list[str] = []
        _, previous_authorities = _manifest_path_authorities(
            previous_payload, root, previous_errors
        )
        errors.extend(_check_manifest_authority_changes(previous_authorities, authorities, payload))

    for rel_path in _active_doc_paths(root):
        if rel_path not in coverage:
            errors.append(
                f"{rel_path}: missing authority classification; add it to "
                f"{DEFAULT_MANIFEST_PATH.as_posix()} with authority, steward, and paths."
            )
        else:
            frontmatter_authority = _frontmatter_authority(root / rel_path)
            manifest_authority = authorities.get(rel_path)
            if frontmatter_authority and frontmatter_authority != manifest_authority:
                errors.append(
                    f"{rel_path}: frontmatter authority '{frontmatter_authority}' "
                    f"conflicts with manifest authority '{manifest_authority}'; update "
                    "frontmatter or manifest so manifest wins."
                )

    errors.extend(_check_transitions(payload, root))
    errors.extend(_check_canonical_doc_reconciliation(payload, root, authorities, changed_paths))
    return errors


def _manifest_path_authorities(
    payload: dict[str, Any], root: Path, errors: list[str]
) -> tuple[dict[str, str], dict[str, str]]:
    coverage: dict[str, str] = {}
    authorities: dict[str, str] = {}
    groups = payload.get("doc_groups", [])
    if not isinstance(groups, list):
        return coverage, authorities

    for index, group in enumerate(groups):
        if not isinstance(group, dict):
            errors.append(f"doc_groups[{index}]: group must be a mapping")
            continue
        group_id = str(group.get("id") or f"index-{index}")
        authority = group.get("authority")
        paths = group.get("paths", [])

        if authority not in ALLOWED_AUTHORITIES:
            errors.append(
                f"doc_groups[{index}]/{group_id}: authority '{authority}' is invalid; "
                f"use one of {', '.join(sorted(ALLOWED_AUTHORITIES))}."
            )
        if not group.get("steward"):
            errors.append(
                f"doc_groups[{index}]/{group_id}: missing steward; add steward owner/role."
            )
        if not isinstance(paths, list) or not paths:
            errors.append(f"doc_groups[{index}]/{group_id}: paths must be a non-empty list.")
            paths = []

        if authority == "derived" and not group.get("source_paths"):
            errors.append(
                f"doc_groups[{index}]/{group_id}: derived group '{group_id}' must "
                "declare source_paths; add canonical source path glob(s)."
            )

        exclude_paths = group.get("exclude_paths", []) or []
        if not isinstance(exclude_paths, list):
            errors.append(
                f"doc_groups[{index}]/{group_id}: exclude_paths must be a list when present."
            )
            exclude_paths = []

        for pattern in paths:
            if not isinstance(pattern, str):
                errors.append(f"doc_groups[{index}]/{group_id}: path pattern must be a string.")
                continue
            matched = _matching_docs(root, pattern, exclude_paths)
            if not matched:
                continue
            for rel_path in matched:
                previous = coverage.get(rel_path)
                if previous and previous != group_id:
                    errors.append(
                        f"{rel_path}: classified by multiple groups ({previous}, {group_id}); "
                        "keep exactly one authority classification."
                    )
                coverage[rel_path] = group_id
                if isinstance(authority, str):
                    authorities[rel_path] = authority

    return coverage, authorities


def _check_schema(payload: dict[str, Any], root: Path, manifest_file: Path) -> list[str]:
    schema_path = payload.get("schema")
    if schema_path is None:
        return []
    if not isinstance(schema_path, str):
        return [f"{_rel(manifest_file, root)}: schema must be a repo-relative path string."]
    schema_file = root / schema_path
    if not schema_file.exists():
        return [f"{schema_path}: missing authority registry JSON schema; restore schema file."]
    try:
        schema = yaml.safe_load(schema_file.read_text(encoding="utf-8")) or {}
        Draft202012Validator.check_schema(schema)
        validator = Draft202012Validator(schema)
        return [
            f"{_rel(manifest_file, root)}: schema violation at "
            f"{'.'.join(str(part) for part in error.absolute_path) or '<root>'}: {error.message}"
            for error in sorted(validator.iter_errors(payload), key=str)
        ]
    except Exception as exc:
        return [f"{schema_path}: invalid authority registry schema: {exc}"]


def _check_derived_source_authority(
    payload: dict[str, Any], root: Path, authorities: dict[str, str]
) -> list[str]:
    errors: list[str] = []
    groups = payload.get("doc_groups", [])
    if not isinstance(groups, list):
        return errors
    for index, group in enumerate(groups):
        if not isinstance(group, dict) or group.get("authority") != "derived":
            continue
        group_id = str(group.get("id") or f"index-{index}")
        source_paths = group.get("source_paths", []) or []
        source_exclude_paths = group.get("source_exclude_paths", []) or []
        if not isinstance(source_paths, list):
            continue
        if not isinstance(source_exclude_paths, list):
            source_exclude_paths = []
        for pattern in source_paths:
            if not isinstance(pattern, str):
                continue
            for rel_path in _matching_docs(root, pattern, source_exclude_paths):
                source_authority = authorities.get(rel_path)
                if source_authority and source_authority != "canonical":
                    errors.append(
                        f"doc_groups[{index}]/{group_id}: source_paths pattern {pattern} "
                        f"matches {rel_path} with authority {source_authority}; "
                        "derived source_paths must resolve only to canonical docs."
                    )
    return errors


def _load_previous_manifest_payload(
    root: Path, rel_manifest: Path, previous_manifest_path: str | Path | None
) -> dict[str, Any] | None:
    if previous_manifest_path:
        previous_file = Path(previous_manifest_path)
        if not previous_file.is_absolute():
            previous_file = root / previous_file
        if not previous_file.exists():
            return None
        payload = yaml.safe_load(previous_file.read_text(encoding="utf-8")) or {}
        return payload if isinstance(payload, dict) else None

    if rel_manifest.is_absolute():
        return None
    try:
        result = subprocess.run(
            ["git", "show", f"origin/main:{rel_manifest.as_posix()}"],
            cwd=root,
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0 or not result.stdout.strip():
        return None
    payload = yaml.safe_load(result.stdout) or {}
    return payload if isinstance(payload, dict) else None


def _check_manifest_authority_changes(
    previous_authorities: dict[str, str],
    current_authorities: dict[str, str],
    payload: dict[str, Any],
) -> list[str]:
    errors: list[str] = []
    transition_index = _transition_index(payload)
    for rel_path, previous_authority in sorted(previous_authorities.items()):
        current_authority = current_authorities.get(rel_path)
        if not current_authority or previous_authority == current_authority:
            continue
        if not _is_protected_transition(previous_authority, current_authority):
            continue
        record = transition_index.get(rel_path)
        if record is None:
            errors.append(
                f"{rel_path}: authority changed from {previous_authority} to {current_authority}; "
                "add one authority_transitions record for this path with approval_evidence."
            )
            continue
        if record.get("from") != previous_authority or record.get("to") != current_authority:
            errors.append(
                f"{rel_path}: authority_transitions record must match manifest change "
                f"from {previous_authority} to {current_authority}."
            )
    return errors


def _transition_index(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    transitions = payload.get("authority_transitions", []) or []
    if not isinstance(transitions, list):
        return index
    for record in transitions:
        if not isinstance(record, dict):
            continue
        changed_paths = record.get("changed_paths", [])
        if isinstance(changed_paths, list) and len(changed_paths) == 1:
            index[str(changed_paths[0])] = record
    return index


def _check_transitions(payload: dict[str, Any], root: Path) -> list[str]:
    errors: list[str] = []
    transitions = payload.get("authority_transitions", []) or []
    if not isinstance(transitions, list):
        return ["authority_transitions: must be a list with one record per changed path."]

    seen_paths: set[str] = set()
    for index, record in enumerate(transitions):
        if not isinstance(record, dict):
            errors.append(f"authority_transitions[{index}]: record must be a mapping.")
            continue
        changed_paths = record.get("changed_paths", [])
        from_class = record.get("from")
        to_class = record.get("to")
        evidence = record.get("approval_evidence") or {}

        if not isinstance(changed_paths, list) or len(changed_paths) != 1:
            errors.append(
                f"authority_transitions[{index}]: changed_paths must contain exactly one path; "
                "use one transition record per path."
            )
            paths = [f"authority_transitions[{index}]"]
        else:
            path = str(changed_paths[0])
            paths = [path]
            if path in seen_paths:
                errors.append(
                    f"authority transition for {path} is duplicated; keep exactly one "
                    "authority_transitions record for this path."
                )
            seen_paths.add(path)

        protected = _is_protected_transition(from_class, to_class)
        if protected:
            for rel_path in paths:
                if evidence.get("type") not in ALLOWED_APPROVAL_TYPES:
                    errors.append(
                        f"authority transition for {rel_path} has invalid approval_evidence.type; "
                        f"use one of {', '.join(sorted(ALLOWED_APPROVAL_TYPES))}."
                    )
                url = evidence.get("url")
                if not isinstance(url, str) or not GITHUB_URL_RE.match(url):
                    errors.append(
                        f"authority transition for {rel_path} approval_evidence.url must "
                        "be a GitHub URL to an issue/PR comment or review."
                    )
                if evidence.get("verdict") != "approved":
                    errors.append(
                        f"authority transition for {rel_path} approval_evidence.verdict "
                        "must be approved."
                    )
    return errors


def _is_protected_transition(from_class: Any, to_class: Any) -> bool:
    if from_class == "discarded" and to_class in ALLOWED_AUTHORITIES - {"discarded"}:
        return True
    return (from_class, to_class) in PROTECTED_TRANSITIONS


def _active_doc_paths(root: Path) -> list[str]:
    docs = root / "docs"
    if not docs.exists():
        return []
    return sorted(
        path.relative_to(root).as_posix()
        for path in docs.rglob("*.md")
        if path.is_file() and not _is_generated_or_vendor_path(path.relative_to(root).as_posix())
    )


def _matching_docs(
    root: Path, pattern: str, exclude_patterns: list[Any] | None = None
) -> list[str]:
    excludes = [str(item) for item in (exclude_patterns or []) if isinstance(item, str)]
    return [
        rel
        for rel in _active_doc_paths(root)
        if _path_matches(rel, pattern) and not any(_path_matches(rel, ex) for ex in excludes)
    ]


def _path_matches(rel_path: str, pattern: str) -> bool:
    regex = ""
    index = 0
    while index < len(pattern):
        char = pattern[index]
        if char == "*":
            if index + 1 < len(pattern) and pattern[index + 1] == "*":
                regex += ".*"
                index += 2
            else:
                regex += "[^/]*"
                index += 1
        elif char == "?":
            regex += "[^/]"
            index += 1
        else:
            regex += re.escape(char)
            index += 1
    return re.fullmatch(regex, rel_path) is not None


def _is_generated_or_vendor_path(rel_path: str) -> bool:
    return rel_path.startswith("docs/LifeOS_Universal_Corpus.md")


def _check_canonical_doc_reconciliation(
    payload: dict[str, Any],
    root: Path,
    authorities: dict[str, str],
    changed_paths: Sequence[str] | None,
) -> list[str]:
    changed = _normalize_changed_paths(changed_paths, root)
    canonical_changed = [
        path
        for path in changed
        if authorities.get(path) == "canonical" and not _is_reconciliation_packet_path(path)
    ]
    if not canonical_changed:
        return []

    packet_paths = [path for path in changed if _is_reconciliation_packet_path(path)]
    packets = [_load_reconciliation_packet(root, path) for path in packet_paths]
    packets = [packet for packet in packets if packet is not None]
    if not packets:
        return [
            f"{path}: missing reconciliation packet or non-semantic exemption for "
            "canonical documentation change; add a packet under "
            "docs/10_meta/reconciliation_packets/."
            for path in canonical_changed
        ]

    errors: list[str] = []
    valid_covered_paths: set[str] = set()
    saw_structurally_valid_packet = False
    for packet_path, packet in packets:
        packet_errors = _validate_reconciliation_exemption(packet_path, packet)
        if packet_errors:
            errors.extend(packet_errors)
            continue
        if "reconciliation_exemption" in packet:
            valid_covered_paths.update(canonical_changed)
            saw_structurally_valid_packet = True
            continue

        packet_errors = _validate_reconciliation_packet(packet_path, packet)
        if packet_errors:
            errors.extend(packet_errors)
            continue
        saw_structurally_valid_packet = True
        valid_covered_paths.update(
            path for path in packet.get("changed_canonical_paths", []) if isinstance(path, str)
        )

    missing = [path for path in canonical_changed if path not in valid_covered_paths]
    if missing and saw_structurally_valid_packet:
        errors.extend(
            f"{path}: reconciliation packet present but stale/irrelevant to changed paths; "
            "changed_canonical_paths must include this canonical doc."
            for path in missing
        )
    elif missing and not errors:
        errors.extend(
            f"{path}: invalid packet; no valid reconciliation packet or exemption "
            "covers this canonical doc."
            for path in missing
        )
    return errors


def _normalize_changed_paths(changed_paths: Sequence[str] | None, root: Path) -> list[str]:
    if changed_paths is None:
        changed_paths = _discover_changed_paths(root)
    return _unique_ordered(
        path.strip().replace("\\", "/")
        for path in changed_paths
        if path and path.strip().endswith(".md") and path.strip().startswith("docs/")
    )


def _discover_changed_paths(root: Path) -> list[str]:
    commands = [
        ["git", "diff", "--name-only", "--diff-filter=ACMR", "origin/main...HEAD"],
        ["git", "diff", "--name-only", "--diff-filter=ACMR"],
        ["git", "diff", "--name-only", "--diff-filter=ACMR", "--cached"],
    ]
    paths: list[str] = []
    for command in commands:
        try:
            result = subprocess.run(
                command,
                cwd=root,
                check=False,
                capture_output=True,
                text=True,
                timeout=5,
            )
        except (OSError, subprocess.TimeoutExpired):
            continue
        if result.returncode == 0:
            paths.extend(line.strip() for line in result.stdout.splitlines() if line.strip())
    return _unique_ordered(paths)


def _is_reconciliation_packet_path(path: str) -> bool:
    return path.startswith(RECONCILIATION_PACKET_PREFIX) and path.endswith(".md")


def _load_reconciliation_packet(root: Path, rel_path: str) -> tuple[str, dict[str, Any]] | None:
    path = root / rel_path
    if not path.exists():
        return rel_path, {}
    text = path.read_text(encoding="utf-8")
    data = _frontmatter_mapping(text)
    if data is None:
        data = _first_yaml_code_block_mapping(text)
    return rel_path, (data if isinstance(data, dict) else {})


def _frontmatter_mapping(text: str) -> dict[str, Any] | None:
    if not text.startswith("---\n"):
        return None
    end = text.find("\n---\n", 4)
    if end == -1:
        return None
    try:
        loaded = yaml.safe_load(text[4:end]) or {}
    except yaml.YAMLError:
        return None
    return loaded if isinstance(loaded, dict) else None


def _first_yaml_code_block_mapping(text: str) -> dict[str, Any] | None:
    match = re.search(r"```ya?ml\n(.*?)\n```", text, flags=re.DOTALL | re.IGNORECASE)
    if not match:
        return None
    try:
        loaded = yaml.safe_load(match.group(1)) or {}
    except yaml.YAMLError:
        return None
    return loaded if isinstance(loaded, dict) else None


def _validate_reconciliation_exemption(packet_path: str, packet: dict[str, Any]) -> list[str]:
    if "reconciliation_exemption" not in packet:
        return []
    exemption = packet.get("reconciliation_exemption")
    if not isinstance(exemption, dict):
        return [f"{packet_path}: invalid packet; reconciliation_exemption must be a mapping."]
    errors: list[str] = []
    reason = exemption.get("reason")
    if reason not in ALLOWED_RECONCILIATION_EXEMPTIONS:
        errors.append(
            f"{packet_path}: invalid reconciliation_exemption.reason '{reason}'; "
            f"use one of {', '.join(sorted(ALLOWED_RECONCILIATION_EXEMPTIONS))}."
        )
    if exemption.get("affected_derived_surfaces") != "none":
        errors.append(
            f"{packet_path}: invalid packet; "
            "reconciliation_exemption.affected_derived_surfaces must be none."
        )
    if exemption.get("semantic_change") is not False:
        errors.append(
            f"{packet_path}: invalid packet; "
            "reconciliation_exemption.semantic_change must be false."
        )
    if reason == "generated-refresh-only" and not exemption.get("source_change_ref"):
        errors.append(
            f"{packet_path}: generated-refresh-only exemption requires source_change_ref."
        )
    return errors


def _validate_reconciliation_packet(packet_path: str, packet: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    missing = sorted(RECONCILIATION_PACKET_REQUIRED_FIELDS - set(packet))
    if missing:
        errors.append(
            f"{packet_path}: invalid packet; missing required field(s): {', '.join(missing)}."
        )
        return errors
    if (
        not isinstance(packet.get("changed_canonical_paths"), list)
        or not packet["changed_canonical_paths"]
    ):
        errors.append(
            f"{packet_path}: invalid packet; changed_canonical_paths must be a non-empty list."
        )
    if not isinstance(packet.get("affected_derived_surfaces"), list):
        errors.append(f"{packet_path}: invalid packet; affected_derived_surfaces must be a list.")
    if not isinstance(packet.get("regeneration_required"), bool):
        errors.append(
            f"{packet_path}: invalid packet; regeneration_required must be true or false."
        )
    for field in ("authority_class_changes", "post_merge_verification_commands"):
        if not isinstance(packet.get(field), list):
            errors.append(f"{packet_path}: invalid packet; {field} must be a list.")
    if packet.get("affected_derived_surfaces") == [] and not packet.get("not_affected_reason"):
        errors.append(
            f"{packet_path}: invalid packet; not_affected_reason is required when "
            "derived surfaces are unaffected."
        )
    return errors


def _frontmatter_authority(path: Path) -> str | None:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return None
    end = text.find("\n---\n", 4)
    if end == -1:
        return None
    try:
        frontmatter = yaml.safe_load(text[4:end]) or {}
    except yaml.YAMLError:
        return None
    if isinstance(frontmatter, dict):
        authority = frontmatter.get("authority")
        if isinstance(authority, str):
            return authority
    return None


def _rel(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()
