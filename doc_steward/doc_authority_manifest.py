"""Documentation authority manifest validator.

The central manifest is the machine authority for LifeOS documentation
classification. Optional per-file frontmatter is derivative and must agree with
this manifest.
"""

from __future__ import annotations

import fnmatch
import re
import subprocess
from pathlib import Path
from typing import Any

import yaml

ALLOWED_AUTHORITIES = {"canonical", "derived", "proposal-only", "deferred", "discarded"}
ALLOWED_APPROVAL_TYPES = {"human", "aa", "ceo"}
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


def check_doc_authority_manifest(
    repo_root: str | Path,
    manifest_path: str | Path | None = None,
    previous_manifest_path: str | Path | None = None,
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
        if fnmatch.fnmatch(rel, pattern) and not any(fnmatch.fnmatch(rel, ex) for ex in excludes)
    ]


def _is_generated_or_vendor_path(rel_path: str) -> bool:
    return rel_path.startswith("docs/LifeOS_Universal_Corpus.md")


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
