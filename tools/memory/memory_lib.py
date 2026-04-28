#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator

AUTHORITY_ORDER = {
    "session_context": 0,
    "observation": 1,
    "agent_memory": 2,
    "shared_knowledge": 3,
    "canonical_doctrine": 4,
}
RECORD_KINDS = {"fact", "preference", "rule", "decision", "state", "lesson", "pattern"}
SCOPES = {"global", "project", "agent", "workflow", "infrastructure"}
LIFECYCLE_STATES = {"draft", "active", "stale", "archived", "superseded", "conflicted"}
SENSITIVITIES = {"public", "internal", "private", "sensitive", "secret"}
RETENTION_CLASSES = {"session", "short", "medium", "long", "permanent"}
AUTHORITY_CLASSES = {"observation", "agent_memory", "shared_knowledge", "canonical_doctrine"}
AUTHORITY_IMPACTS = {"none", "low", "medium", "high"}
PROPOSED_ACTIONS = {"create", "update", "supersede", "conflict_open", "archive"}
CLASSIFICATIONS = {
    "discard",
    "session_only",
    "observation",
    "agent_memory_candidate",
    "shared_knowledge_candidate",
    "canonical_doctrine_candidate",
    "conflict_candidate",
    "archive_candidate",
}
STAGING_STATUSES = {
    "workorder_distillation",
    "candidate_packet",
    "memory_candidate",
    "promotion_candidate",
    "conflict_candidate",
    "prune_candidate",
    "review_digest",
}
SOURCE_TYPES = {
    "conversation",
    "workorder",
    "repo_file",
    "commit",
    "issue",
    "pull_request",
    "receipt",
    "manual_note",
    "external_doc",
}
CONFLICT_TYPES = {
    "contradiction",
    "duplicate",
    "scope_mismatch",
    "staleness",
    "authority_collision",
    "evidence_dispute",
}
CONFLICT_STATUSES = {"open", "acknowledged", "blocked", "resolved", "archived"}
MATERIALITIES = {"low", "medium", "high"}
SUPERSESSION_TYPES = {"replaces", "narrows", "broadens", "corrects", "archives"}
DISPOSITIONS = {"accepted", "rejected", "staged", "merged"}
WRITER_ALLOWED = "COO"
SHA_RE = re.compile(r"\b[0-9a-f]{40}\b")


@dataclass(frozen=True)
class LoadedRecord:
    path: Path
    front_matter: dict[str, Any]
    body: str


def repo_root(start: Path | None = None) -> Path:
    current = (start or Path.cwd()).resolve()
    for candidate in [current, *current.parents]:
        if (candidate / ".git").exists() and (candidate / "docs").exists():
            return candidate
    return current


def load_schema(repo: Path, schema_name: str) -> dict[str, Any]:
    path = repo / "schemas" / "memory" / schema_name
    return json.loads(path.read_text(encoding="utf-8"))


def validate_json_schema(repo: Path, schema_name: str, payload: dict[str, Any]) -> list[str]:
    schema = load_schema(repo, schema_name)
    validator = Draft202012Validator(schema)
    return [
        f"{'/'.join(str(p) for p in error.path) or '<root>'}: {error.message}"
        for error in sorted(validator.iter_errors(payload), key=lambda e: list(e.path))
    ]


def split_front_matter(text: str) -> tuple[dict[str, Any], str]:
    if not text.startswith("---\n"):
        raise ValueError("missing YAML front matter")
    end = text.find("\n---", 4)
    if end == -1:
        raise ValueError("unterminated YAML front matter")
    raw = text[4:end]
    body = text[end + 4 :].lstrip("\n")
    payload = yaml.safe_load(raw) or {}
    if not isinstance(payload, dict):
        raise ValueError("front matter must be a mapping")
    return payload, body


def read_record(path: Path) -> LoadedRecord:
    text = path.read_text(encoding="utf-8")
    front_matter, body = split_front_matter(text)
    return LoadedRecord(path=path, front_matter=front_matter, body=body)


def write_front_matter(path: Path, payload: dict[str, Any], body: str) -> None:
    text = "---\n" + yaml.safe_dump(payload, sort_keys=False, allow_unicode=False) + "---\n" + body
    path.write_text(text, encoding="utf-8")


def iter_yaml_markdown_files(target: Path) -> list[Path]:
    if target.is_file():
        return [target]
    paths: list[Path] = []
    for pattern in ("*.md", "*.yaml", "*.yml", "*.json"):
        paths.extend(path for path in target.rglob(pattern) if path.is_file())
    return sorted(set(paths))


def relpath(path: Path, repo: Path) -> str:
    try:
        return path.resolve().relative_to(repo.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def is_under(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def iso_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def has_commit_stable_provenance(source: dict[str, Any]) -> bool:
    source_type = source.get("source_type")
    locator = str(source.get("locator") or "")
    commit_sha = str(source.get("commit_sha") or "")
    content_hash = str(source.get("content_hash") or "")
    if source_type not in {"repo_file", "commit"}:
        return True
    return bool(
        SHA_RE.fullmatch(commit_sha) or SHA_RE.search(locator) or content_hash.startswith("sha256:")
    )


def listify(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]
