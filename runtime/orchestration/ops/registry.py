from __future__ import annotations

import os
import re
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_WORKSPACE_ALIAS = "/workspace/"
_DEFAULT_OPENCLAW_WORKSPACE = Path.home() / ".openclaw" / "workspace"
_OP_NOTE_DIR = Path("artifacts") / "coo" / "notes"
_TITLE_SLUG_RE = re.compile(r"[^a-z0-9]+")


class OperationValidationError(ValueError):
    pass


@dataclass(frozen=True)
class ActionSpec:
    action_id: str
    operation_kind: str
    requires_approval: bool


_ACTION_SPECS: dict[str, ActionSpec] = {
    "workspace.file.write": ActionSpec(
        action_id="workspace.file.write",
        operation_kind="mutation",
        requires_approval=True,
    ),
    "workspace.file.edit": ActionSpec(
        action_id="workspace.file.edit",
        operation_kind="mutation",
        requires_approval=True,
    ),
    "lifeos.note.record": ActionSpec(
        action_id="lifeos.note.record",
        operation_kind="mutation",
        requires_approval=True,
    ),
}


def resolve_openclaw_workspace_root() -> Path:
    raw = os.environ.get("OPENCLAW_WORKSPACE", "").strip()
    root = Path(raw).expanduser() if raw else _DEFAULT_OPENCLAW_WORKSPACE
    return root.resolve()


def get_action_spec(action_id: str) -> ActionSpec:
    spec = _ACTION_SPECS.get(action_id)
    if spec is None:
        raise OperationValidationError(f"Unsupported action_id: {action_id}")
    return spec


def is_known_action(action_id: str) -> bool:
    return action_id in _ACTION_SPECS


def _slugify_title(value: str) -> str:
    slug = _TITLE_SLUG_RE.sub("-", value.strip().lower()).strip("-")
    return slug[:80] or "note"


def _normalize_workspace_relative_path(path_value: str) -> str:
    candidate = str(path_value).strip()
    if not candidate:
        raise OperationValidationError("args.path is required")
    if candidate.startswith(_WORKSPACE_ALIAS):
        candidate = candidate[len(_WORKSPACE_ALIAS) :]
    elif candidate.startswith("/workspace"):
        candidate = candidate.removeprefix("/workspace").lstrip("/")
    elif candidate.startswith("/"):
        raise OperationValidationError("args.path must be relative or use the /workspace/... alias")
    candidate = candidate.lstrip("/")
    if not candidate:
        raise OperationValidationError("args.path must resolve within the workspace root")
    return candidate


def normalize_workspace_path(path_value: str, workspace_root: Path | None = None) -> Path:
    root = (workspace_root or resolve_openclaw_workspace_root()).resolve()
    relative = _normalize_workspace_relative_path(path_value)
    resolved = (root / relative).resolve()
    if resolved != root and root not in resolved.parents:
        raise OperationValidationError(f"Resolved path escapes workspace root: {path_value}")
    return resolved


def _path_arg(args: dict[str, Any]) -> str:
    for key in ("path", "file_path"):
        value = str(args.get(key, "")).strip()
        if value:
            return value
    return ""


def _normalize_write_args(args: dict[str, Any], workspace_root: Path) -> dict[str, Any]:
    path_value = _path_arg(args)
    content = args.get("content")
    if not isinstance(content, str):
        raise OperationValidationError("workspace.file.write requires string args.content")
    resolved = normalize_workspace_path(path_value, workspace_root)
    return {
        "path": path_value,
        "resolved_path": str(resolved),
        "content": content,
    }


def _normalize_edit_args(args: dict[str, Any], workspace_root: Path) -> dict[str, Any]:
    path_value = _path_arg(args)
    old_text = args.get("old_text")
    new_text = args.get("new_text")
    if not isinstance(old_text, str) or not isinstance(new_text, str):
        raise OperationValidationError(
            "workspace.file.edit requires string args.old_text and args.new_text"
        )
    if old_text == "":
        raise OperationValidationError("workspace.file.edit args.old_text must be non-empty")
    resolved = normalize_workspace_path(path_value, workspace_root)
    return {
        "path": path_value,
        "resolved_path": str(resolved),
        "old_text": old_text,
        "new_text": new_text,
    }


def _normalize_note_args(args: dict[str, Any], workspace_root: Path) -> dict[str, Any]:
    title = str(args.get("title", "")).strip()
    content = args.get("content")
    raw_tags = args.get("tags") or []
    if not title:
        raise OperationValidationError("lifeos.note.record requires args.title")
    if not isinstance(content, str):
        raise OperationValidationError("lifeos.note.record requires string args.content")
    if not isinstance(raw_tags, list) or not all(isinstance(tag, str) for tag in raw_tags):
        raise OperationValidationError("lifeos.note.record args.tags must be a list of strings")
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    filename = f"{datetime.now(timezone.utc).strftime('%Y-%m-%d')}-{_slugify_title(title)}.md"
    resolved = (workspace_root / _OP_NOTE_DIR / filename).resolve()
    if workspace_root not in resolved.parents:
        raise OperationValidationError("lifeos.note.record resolved path escapes workspace root")
    return {
        "title": title,
        "content": content,
        "tags": list(raw_tags),
        "timestamp": timestamp,
        "resolved_path": str(resolved),
        "path": str((_OP_NOTE_DIR / filename).as_posix()),
    }


def validate_operation(action_id: str, args: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(args, dict):
        raise OperationValidationError("args must be a mapping")
    workspace_root = resolve_openclaw_workspace_root()
    spec = get_action_spec(action_id)

    normalizers = {
        "workspace.file.write": _normalize_write_args,
        "workspace.file.edit": _normalize_edit_args,
        "lifeos.note.record": _normalize_note_args,
    }
    normalized = normalizers[action_id](deepcopy(args), workspace_root)
    normalized["workspace_root"] = str(workspace_root)
    normalized["action_id"] = spec.action_id
    normalized["operation_kind"] = spec.operation_kind
    normalized["requires_approval"] = spec.requires_approval
    return normalized


def validate_action(action_id: str, args: dict[str, Any]) -> dict[str, Any]:
    return validate_operation(action_id, args)
